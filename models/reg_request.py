# -*- coding: utf-8 -*-
"""Requests from other departments (طلبات الخدمة القانونية).

Any employee asks; the legal team triages: accept (a matter is opened from the
request and linked to it), return for completion with a reason, or decline with
a reason. The requester sees the status and, once a matter exists, only its
number, status and next date: never its notes, files or people."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .ldm_engine import engine_guard, in_engine
from .reg_common import adopt_attachments

REQUESTER_WRITABLE = {"name", "description", "needed_by", "attachment_ids"}
REQUEST_GUARDED = {"state", "task_id", "assigned_user_id", "return_reason"}
REQUESTER_OPEN_STATES = ("new", "returned")
LEGAL_GROUP = "legal_department_management.group_ldm_clerk"
LAWYER_GROUP = "legal_department_management.group_legal_user"

REQUEST_TYPES = [
    ("contract", "Contract review"), ("opinion", "Legal opinion"), ("poa", "Power of attorney"),
    ("government", "Government transaction"), ("dispute", "Dispute or lawsuit"), ("other", "Other"),
]
# Used when no matter type is marked for a kind of request.
FALLBACK_TEMPLATES = {
    "contract": "ldm_template_contract_review",
    "opinion": "ldm_template_opinion",
    "poa": "ldm_template_poa",
    "government": "ldm_template_government",
    "dispute": "ldm_template_civil_lawsuit",
    "other": "ldm_template_consultation",
}


def _task_states(model):
    # A selection given as a function is not translated by Odoo: return the
    # matter's labels already translated into the reader's language.
    return model.env["legal.task"]._fields["state"]._description_selection(model.env)


class LegalTaskTemplate(models.Model):
    _inherit = "legal.task.template"

    request_type = fields.Selection(REQUEST_TYPES, string="Used for requests of kind",
                                    help="When the legal team accepts a request of this kind, the new matter "
                                    "starts from this type.")


class LegalRequest(models.Model):
    _inherit = "legal.request"

    matter_number = fields.Char(string="Matter number", compute="_compute_matter_status", compute_sudo=True)
    matter_state = fields.Selection(selection=_task_states, string="Matter status",
                                    compute="_compute_matter_status", compute_sudo=True)
    matter_next_date = fields.Date(string="Next date", compute="_compute_matter_status", compute_sudo=True)
    date_submitted = fields.Date(string="Sent on", readonly=True, copy=False,
                                 default=fields.Date.context_today)
    ldm_is_legal = fields.Boolean(compute="_compute_ldm_rights")
    ldm_is_requester = fields.Boolean(compute="_compute_ldm_rights")
    ldm_can_triage = fields.Boolean(compute="_compute_ldm_rights")

    @api.depends("task_id")
    def _compute_matter_status(self):
        for request in self:
            task = request.task_id
            request.matter_number = task.task_number or False
            request.matter_state = task.state or False
            request.matter_next_date = task.next_date or False

    @api.depends_context("uid")
    @api.depends("requester_id", "state")
    def _compute_ldm_rights(self):
        user = self.env.user
        legal = user.has_group(LEGAL_GROUP)
        lawyer = user.has_group(LAWYER_GROUP)
        for request in self:
            request.ldm_is_legal = legal
            request.ldm_is_requester = request.requester_id == user
            request.ldm_can_triage = lawyer and request.state in ("new", "in_review")

    # ------------------------------------------------------------------
    # CRUD: the requester writes the question, the legal team the answer
    # ------------------------------------------------------------------
    def _ldm_is_legal(self):
        return self.env.user.has_group(LEGAL_GROUP) or self.env.su

    @api.model_create_multi
    def create(self, vals_list):
        trusted = in_engine() or self.env.su
        legal = self._ldm_is_legal()
        for vals in vals_list:
            if not trusted:
                for field in REQUEST_GUARDED:
                    vals.pop(field, None)
            if not legal:
                # An employee asks for themselves; the client is set at triage.
                vals["requester_id"] = self.env.uid
                vals.pop("legal_company_id", None)
        requests = super().create(vals_list)
        adopt_attachments(requests)
        for request in requests:
            request._ldm_notify_team()
        return requests

    def write(self, vals):
        if not (in_engine() or self.env.su):
            if REQUEST_GUARDED & set(vals):
                raise AccessError(_("A request moves through Accept, Return, Decline or Resubmit; its status, "
                                    "matter and handler cannot be edited."))
            if not self._ldm_is_legal():
                extra = set(vals) - REQUESTER_WRITABLE
                if extra:
                    raise AccessError(_("You can change what you asked, the details, the date and the files. "
                                        "The legal team sets the rest."))
                for request in self:
                    if request.requester_id != self.env.user:
                        raise AccessError(_("This request is not yours."))
                    if request.state not in REQUESTER_OPEN_STATES:
                        raise UserError(_("The legal team is working on “%s”: it can only be changed if they "
                                          "return it to you.", request.name))
        result = super().write(vals)
        if "attachment_ids" in vals:
            adopt_attachments(self)
        return result

    # ------------------------------------------------------------------
    # Triage
    # ------------------------------------------------------------------
    def _ldm_check_triage(self):
        if not self.env.user.has_group(LAWYER_GROUP):
            raise AccessError(_("Only a lawyer of the legal team can accept, return or decline a request."))
        for request in self:
            if request.state not in ("new", "in_review"):
                raise UserError(_("“%s” has already been answered.", request.name))

    def _ldm_notify_team(self):
        """A new or resubmitted request: a note in its chatter that the legal
        managers follow, so it reaches them without a dashboard."""
        self.ensure_one()
        managers = self.env.ref("legal_department_management.group_legal_manager").sudo().all_user_ids.filtered(
            lambda u: u.active and not u.share and self.company_id in u.company_ids)
        partners = (managers.partner_id | self.assigned_user_id.partner_id) - self.env.user.partner_id
        if partners:
            self.sudo().message_subscribe(partner_ids=partners.ids)
        self.message_post(body=_("Sent to the legal team."), partner_ids=partners.ids,
                          subtype_xmlid="mail.mt_comment")

    def action_ldm_take(self):
        self._ldm_check_triage()
        with engine_guard():
            self.write({"assigned_user_id": self.env.uid, "state": "in_review"})
        for request in self:
            request.message_post(body=_("%s is looking at this request.", self.env.user.name))
        return True

    def action_ldm_accept(self):
        self.ensure_one()
        self._ldm_check_triage()
        return {
            "type": "ir.actions.act_window",
            "name": _("Accept: open a matter"),
            "res_model": "legal.reg.matter.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _ldm_default_template(self):
        self.ensure_one()
        template = self.env["legal.task.template"].search([("request_type", "=", self.request_type)], limit=1)
        if not template:
            template = self.env.ref(f"legal_department_management.{FALLBACK_TEMPLATES[self.request_type]}",
                                    raise_if_not_found=False)
        return template or self.env["legal.task.template"]

    def _ldm_link_matter(self, task):
        """The request is accepted: the matter carries the request, the
        requester and the files they sent."""
        self.ensure_one()
        with engine_guard():
            self.write({"state": "accepted", "task_id": task.id,
                        "assigned_user_id": self.assigned_user_id.id or self.env.uid})
        task.sudo().write({"request_id": self.id, "requester_id": self.requester_id.id})
        # The files are copied, not shared: the matter's people must be able to
        # open them without access to the requests register.
        copies = self.env["ir.attachment"]
        for attachment in self.sudo().attachment_ids:
            copies |= attachment.copy({"res_model": "legal.task", "res_id": task.id})
        if copies:
            task.sudo().write({"attachment_ids": [(4, a.id) for a in copies]})
        self.message_post(body=_("Accepted. The legal team opened matter %s.", task.task_number),
                          partner_ids=self.requester_id.partner_id.ids,
                          subtype_xmlid="mail.mt_comment")
        task.message_post(body=_("Opened from the request of %(who)s: %(what)s",
                                 who=self.requester_id.name, what=self.name))

    def action_ldm_return(self):
        return self._ldm_open_reason("return")

    def action_ldm_decline(self):
        return self._ldm_open_reason("decline")

    def _ldm_open_reason(self, mode):
        self.ensure_one()
        self._ldm_check_triage()
        return {
            "type": "ir.actions.act_window",
            "name": _("Return to the requester") if mode == "return" else _("Decline the request"),
            "res_model": "legal.request.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id, "default_mode": mode},
        }

    def _ldm_return(self, reason):
        self._ldm_check_triage()
        if not (reason or "").strip():
            raise UserError(_("Say what is missing, so the requester can complete it."))
        with engine_guard():
            self.write({"state": "returned", "return_reason": reason})
        for request in self:
            request.message_post(body=_("Returned for completion: %s", reason),
                                 partner_ids=request.requester_id.partner_id.ids, subtype_xmlid="mail.mt_comment")
        return True

    def _ldm_decline(self, reason):
        self._ldm_check_triage()
        if not (reason or "").strip():
            raise UserError(_("Say why the request is declined."))
        with engine_guard():
            self.write({"state": "rejected", "return_reason": reason})
        for request in self:
            request.message_post(body=_("Declined: %s", reason),
                                 partner_ids=request.requester_id.partner_id.ids, subtype_xmlid="mail.mt_comment")
        return True

    def action_ldm_resubmit(self):
        for request in self:
            if request.state != "returned":
                raise UserError(_("Only a request returned to you can be sent again."))
            if request.requester_id != self.env.user and not self.env.user.has_group(LAWYER_GROUP):
                raise AccessError(_("Only the person who asked can send the request again."))
            with engine_guard():
                request.write({"state": "new", "return_reason": False})
            request.message_post(body=_("Completed and sent again."))
            request._ldm_notify_team()
        return True

    def action_ldm_send_result(self):
        self.ensure_one()
        if not self.env.user.has_group(LAWYER_GROUP):
            raise AccessError(_("Only a lawyer of the legal team can send the result."))
        if self.state != "accepted" or not self.task_id:
            raise UserError(_("Accept the request and work on its matter before sending a result."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Send the result to %s", self.requester_id.name),
            "res_model": "legal.request.result.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _ldm_send_result(self, attachments, message):
        """Copy the chosen files of the matter onto the request (the requester
        cannot open the matter) and tell the requester."""
        self.ensure_one()
        copies = self.env["ir.attachment"]
        for attachment in attachments.sudo():
            copies |= attachment.copy({"res_model": self._name, "res_id": self.id})
        if copies:
            self.sudo().write({"attachment_ids": [(4, a.id) for a in copies]})
        body = message or _("The legal team sent you the result.")
        self.message_post(body=body, attachment_ids=copies.ids, partner_ids=self.requester_id.partner_id.ids,
                          subtype_xmlid="mail.mt_comment")
        return copies

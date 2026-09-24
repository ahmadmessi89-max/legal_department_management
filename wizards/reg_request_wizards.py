# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class LegalRegMatterWizard(models.TransientModel):
    """Open a matter from a request (accepting it) or from a letter. A short
    quick-create: the matter type, the client, the title and one date, filled
    in from the source; the matter is built by ``create_from_template`` and
    linked back to where it came from."""

    _name = "legal.reg.matter.wizard"
    _description = "Open a matter from a request or a letter"

    request_id = fields.Many2one("legal.request", string="Request", ondelete="cascade")
    correspondence_id = fields.Many2one("legal.correspondence", string="Letter", ondelete="cascade")
    template_id = fields.Many2one("legal.task.template", string="Matter type")
    legal_company_id = fields.Many2one("legal.company", string="Client")
    department_id = fields.Many2one("legal.department", string="Body or court")
    lawyer_id = fields.Many2one("res.users", string="Responsible",
                                domain="[('share', '=', False)]")
    name = fields.Char(string="Title")
    key_date = fields.Date(string="Target date",
                           help="For a lawsuit, the date of the first session; otherwise the date the work is due.")
    source_summary = fields.Text(string="What was asked", compute="_compute_source_summary")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        request = self.env["legal.request"].browse(values.get("request_id")) if values.get("request_id") else False
        letter = self.env["legal.correspondence"].browse(values.get("correspondence_id")) \
            if values.get("correspondence_id") else False
        if request:
            template = request._ldm_default_template()
            values.setdefault("template_id", template.id or False)
            values.setdefault("legal_company_id", request.legal_company_id.id or False)
            values.setdefault("name", request.name)
            values.setdefault("key_date", request.needed_by or False)
            values.setdefault("lawyer_id", (request.assigned_user_id or self.env.user).id)
            values.setdefault("department_id", template.department_id.id or False)
        elif letter:
            values.setdefault("legal_company_id", letter.legal_company_id.id or False)
            values.setdefault("department_id", letter.department_id.id or False)
            values.setdefault("name", letter.name)
            values.setdefault("key_date", letter.reply_due_date or letter.instruction_due or False)
            values.setdefault("lawyer_id", (letter.assigned_user_id or self.env.user).id)
        return values

    @api.depends("request_id", "correspondence_id")
    def _compute_source_summary(self):
        for wizard in self:
            if wizard.request_id:
                wizard.source_summary = wizard.request_id.description or wizard.request_id.name
            elif wizard.correspondence_id:
                wizard.source_summary = wizard.correspondence_id.referral_note or wizard.correspondence_id.name
            else:
                wizard.source_summary = False

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id.department_id and not self.department_id:
            self.department_id = self.template_id.department_id

    def action_create(self):
        self.ensure_one()
        if not self.legal_company_id:
            raise UserError(_("Choose the client the matter is for."))
        if not self.template_id:
            raise UserError(_("Choose the matter type: it fills in the steps and the documents to collect."))
        if self.request_id:
            self.request_id._ldm_check_triage()
            if not self.request_id.legal_company_id:
                self.request_id.sudo().legal_company_id = self.legal_company_id
        if self.correspondence_id:
            self.correspondence_id.check_access("write")
            if self.correspondence_id.task_id:
                raise UserError(_("This letter already belongs to %s.", self.correspondence_id.task_id.display_name))
        vals = {
            "template_id": self.template_id.id,
            "legal_company_id": self.legal_company_id.id,
            "name": self.name or False,
            "key_date": self.key_date or False,
        }
        if self.department_id:
            vals["department_id"] = self.department_id.id
        if self.lawyer_id:
            vals["lawyer_id"] = self.lawyer_id.id
        task = self.env["legal.task"].browse(self.env["legal.task"].create_from_template(vals))
        if self.request_id:
            self.request_id._ldm_link_matter(task)
        if self.correspondence_id:
            letter = self.correspondence_id
            letter.write({"task_id": task.id, "legal_company_id": letter.legal_company_id.id or task.legal_company_id.id})
            if letter.state == "registered":
                letter._ldm_sync_deadlines()
            task.message_post(body=_("Opened from letter %s.", letter.display_name))
            letter.message_post(body=_("Matter %s opened from this letter.", task.task_number))
        return {
            "type": "ir.actions.act_window",
            "res_model": "legal.task",
            "res_id": task.id,
            "view_mode": "form",
            "target": "current",
        }


class LegalRequestReasonWizard(models.TransientModel):
    _name = "legal.request.reason.wizard"
    _description = "Return or decline a request"

    request_id = fields.Many2one("legal.request", string="Request", required=True, ondelete="cascade")
    mode = fields.Selection([("return", "Return for completion"), ("decline", "Decline")], required=True,
                            default="return")
    reason = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        if self.mode == "return":
            self.request_id._ldm_return(self.reason)
        else:
            self.request_id._ldm_decline(self.reason)
        return {"type": "ir.actions.act_window_close"}


class LegalRequestResultWizard(models.TransientModel):
    """Send the requester the result: chosen files of the matter are copied
    onto the request, because the requester cannot open the matter."""

    _name = "legal.request.result.wizard"
    _description = "Send the result to the requester"

    request_id = fields.Many2one("legal.request", string="Request", required=True, ondelete="cascade")
    available_attachment_ids = fields.Many2many("ir.attachment", "legal_request_result_available_rel",
                                                "wizard_id", "attachment_id", compute="_compute_available")
    attachment_ids = fields.Many2many("ir.attachment", "legal_request_result_attachment_rel", "wizard_id",
                                      "attachment_id", string="Files to send",
                                      domain="[('id', 'in', available_attachment_ids)]")
    message = fields.Text(string="Message", default=lambda self: _("Here is the result of your request."))

    @api.depends("request_id")
    def _compute_available(self):
        for wizard in self:
            task = wizard.request_id.task_id
            files = task.attachment_ids | self.env["ir.attachment"].search(
                [("res_model", "=", "legal.task"), ("res_id", "=", task.id)]) if task else self.env["ir.attachment"]
            wizard.available_attachment_ids = files

    def action_send(self):
        self.ensure_one()
        if not self.env.user.has_group("legal_department_management.group_legal_user"):
            raise AccessError(_("Only a lawyer of the legal team can send the result."))
        allowed = self.available_attachment_ids
        if self.attachment_ids - allowed:
            raise UserError(_("Only files of the request's matter can be sent."))
        self.request_id._ldm_send_result(self.attachment_ids, self.message)
        return {"type": "ir.actions.act_window_close"}

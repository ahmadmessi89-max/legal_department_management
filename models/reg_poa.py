# -*- coding: utf-8 -*-
"""Powers of attorney (الوكالات): expiry, revocation, the matters that rely on
them, and "who can act for this client before this body today"."""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain

from .ldm_engine import engine_guard, in_engine
from .reg_common import close_activities, sync_deadline

POA_GUARDED = {"state", "revoked_date", "revoke_reason"}
OPEN_TASK_STATES = ("draft", "in_progress", "pending_docs")


class LdmRegScanMixin(models.AbstractModel):
    """An upload box for the ``attachment_id`` scan of a register record. Odoo
    has no upload widget for a Many2one to an attachment, so the file is shown
    as a binary field that reads and writes the attachment."""

    _name = "ldm.reg.scan.mixin"
    _description = "Scanned copy of a register record"

    attachment_id = fields.Many2one("ir.attachment", string="Scan", ondelete="set null")
    scan = fields.Binary(string="Scanned copy", compute="_compute_scan", inverse="_inverse_scan")
    scan_name = fields.Char(string="File name", compute="_compute_scan", inverse="_inverse_scan")

    @api.depends("attachment_id")
    def _compute_scan(self):
        for record in self:
            record.scan = record.attachment_id.datas
            record.scan_name = record.attachment_id.name

    def _inverse_scan(self):
        for record in self:
            if not record.scan:
                record.attachment_id = False
                continue
            name = record.scan_name or _("Scan of %s", record.display_name)
            if record.attachment_id and record.attachment_id.datas == record.scan:
                if record.attachment_id.name != name:
                    record.attachment_id.name = name
                continue
            record.attachment_id = self.env["ir.attachment"].create({
                "name": name, "datas": record.scan, "res_model": record._name, "res_id": record.id,
            })


class LegalPoa(models.Model):
    _name = "legal.poa"
    _inherit = ["legal.poa", "ldm.reg.scan.mixin"]

    expiry_status = fields.Selection(
        [("none", "No expiry date"), ("valid", "Valid"), ("expiring", "Expires soon"), ("expired", "Expired"),
         ("revoked", "Revoked")],
        string="Validity", compute="_compute_expiry_status", search="_search_expiry_status")
    days_to_expiry = fields.Integer(string="Days left", compute="_compute_expiry_status")
    task_count = fields.Integer(string="Matters", compute="_compute_task_count")
    open_task_count = fields.Integer(string="Open matters relying on it", compute="_compute_task_count")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("state", "date_expiry", "company_id.ldm_poa_warning_days")
    def _compute_expiry_status(self):
        today = fields.Date.context_today(self)
        for poa in self:
            poa.days_to_expiry = (poa.date_expiry - today).days if poa.date_expiry else 0
            warn = poa.company_id.ldm_poa_warning_days or 30
            if poa.state == "revoked":
                poa.expiry_status = "revoked"
            elif poa.state == "expired" or (poa.date_expiry and poa.date_expiry < today):
                poa.expiry_status = "expired"
            elif not poa.date_expiry:
                poa.expiry_status = "none"
            elif poa.days_to_expiry <= warn:
                poa.expiry_status = "expiring"
            else:
                poa.expiry_status = "valid"

    def _search_expiry_status(self, operator, value):
        if operator not in ("=", "!=", "in", "not in"):
            return NotImplemented
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=self.env.company.ldm_poa_warning_days or 30)
        live = Domain("state", "=", "active")
        domains = {
            "revoked": Domain("state", "=", "revoked"),
            "expired": Domain("state", "=", "expired") | (live & Domain("date_expiry", "<", today)),
            "none": live & Domain("date_expiry", "=", False),
            "expiring": live & Domain("date_expiry", ">=", today) & Domain("date_expiry", "<=", soon),
            "valid": live & Domain("date_expiry", ">", soon),
        }
        values = [value] if isinstance(value, str) else list(value)
        domain = Domain.OR([domains[v] for v in values if v in domains] or [Domain.FALSE])
        return domain if operator in ("=", "in") else ~domain

    def _compute_task_count(self):
        Task = self.env["legal.task"]
        totals = {p.id: n for p, n in Task._read_group([("poa_id", "in", self.ids)], ["poa_id"], ["__count"])}
        opened = {p.id: n for p, n in Task._read_group(
            [("poa_id", "in", self.ids), ("state", "in", OPEN_TASK_STATES)], ["poa_id"], ["__count"])}
        for poa in self:
            poa.task_count = totals.get(poa.id, 0)
            poa.open_task_count = opened.get(poa.id, 0)

    # ------------------------------------------------------------------
    # CRUD: the status moves only through revocation and the calendar
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not (in_engine() or self.env.su):
            for vals in vals_list:
                for field in POA_GUARDED:
                    vals.pop(field, None)
        poas = super().create(vals_list)
        poas._ldm_sync_expiry()
        return poas

    def write(self, vals):
        if not (in_engine() or self.env.su) and POA_GUARDED & set(vals):
            raise AccessError(_("A power of attorney ends by its expiry date or through “Revoke”. "
                                "Its status cannot be edited by hand."))
        result = super().write(vals)
        if {"date_expiry", "state", "principal_company_id", "company_id"} & set(vals) and not self.env.context.get(
                "ldm_poa_syncing"):
            self._ldm_sync_expiry()
        return result

    # ------------------------------------------------------------------
    # Expiry and its deadline
    # ------------------------------------------------------------------
    def _ldm_responsible(self):
        self.ensure_one()
        user = self.principal_company_id.lawyer_id or self.agent_user_ids[:1]
        return user.filtered(lambda u: u.active and not u.share)

    def _ldm_sync_expiry(self):
        """Mark a power of attorney expired once its date has passed (and live
        again if the date is moved forward), and keep exactly one open expiry
        deadline while it is inside the warning window."""
        today = fields.Date.context_today(self)
        for poa in self.with_context(ldm_poa_syncing=True):
            if poa.state != "revoked":
                target = "expired" if poa.date_expiry and poa.date_expiry < today else "active"
                if poa.state != target:
                    with engine_guard():
                        poa.write({"state": target})
                    if target == "expired":
                        poa.message_post(body=_("This power of attorney expired on %s.", poa.date_expiry))
                        poa._ldm_flag_matters(_("expired on %s", poa.date_expiry))
            poa._ldm_sync_deadline(today)

    def _ldm_sync_deadline(self, today):
        self.ensure_one()
        warn = self.company_id.ldm_poa_warning_days or 30
        if self.state == "active" and self.date_expiry and self.date_expiry <= today + timedelta(days=warn):
            sync_deadline(self, "expiry", {
                "name": _("Power of attorney expires: %s", self.name),
                "date_safe": self.date_expiry,
                "date_deadline": self.date_expiry,
                "user_id": self._ldm_responsible().id or False,
                "legal_company_id": self.principal_company_id.id or False,
                "company_id": self.company_id.id,
            })
        else:
            # Revoked: nothing left to renew. Renewed or given a later date: the
            # reminder was answered. Expired: left open for the deadline engine.
            close = {"revoked": "cancelled", "active": "done"}.get(self.state)
            sync_deadline(self, "expiry", None, close_state=close)

    @api.model
    def _cron_ldm_poa_expiry(self):
        """Daily: expire the powers of attorney whose date has passed and keep
        one expiry deadline for each one inside the warning window."""
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=max(self.env["res.company"].search([]).mapped("ldm_poa_warning_days") or [30]))
        self.search([("state", "=", "active"), ("date_expiry", "!=", False), ("date_expiry", "<=", horizon)])._ldm_sync_expiry()
        # Deadlines of powers of attorney that left the window (renewed, revoked) are closed too.
        stale = self.env["legal.deadline"].sudo().search([("source_model", "=", self._name), ("kind", "=", "expiry"),
                                                           ("state", "=", "open")])
        self.browse(stale.mapped("source_id")).exists()._ldm_sync_expiry()
        return True

    # ------------------------------------------------------------------
    # Revocation (عزل الوكيل)
    # ------------------------------------------------------------------
    def action_ldm_revoke(self):
        self.ensure_one()
        if self.state == "revoked":
            raise UserError(_("%s is already revoked.", self.display_name))
        return {
            "type": "ir.actions.act_window",
            "name": _("Revoke power of attorney"),
            "res_model": "legal.poa.revoke.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_poa_id": self.id},
        }

    def _ldm_revoke(self, date, reason):
        if not self.env.user.has_group("legal_department_management.group_legal_user"):
            raise AccessError(_("Only a lawyer can revoke a power of attorney."))
        if not (reason or "").strip():
            raise UserError(_("Say why the power of attorney is revoked."))
        self.check_access("write")
        for poa in self:
            if poa.state == "revoked":
                raise UserError(_("%s is already revoked.", poa.display_name))
            with engine_guard():
                poa.write({"state": "revoked", "revoked_date": date, "revoke_reason": reason})
            poa.message_post(body=_("Revoked on %(date)s by %(user)s: %(reason)s",
                                    date=date, user=self.env.user.name, reason=reason))
            poa._ldm_flag_matters(_("was revoked on %(date)s: %(reason)s", date=date, reason=reason))
            poa._ldm_close_reminders()
        return True

    def _ldm_flag_matters(self, what):
        """Tell the people on every open matter that relies on this power of
        attorney: a note on the matter and a to-do for its responsible."""
        activity_type = self.env.ref("legal_department_management.ldm_activity_expiry", raise_if_not_found=False)
        for poa in self:
            tasks = self.env["legal.task"].sudo().search([("poa_id", "=", poa.id), ("state", "in", OPEN_TASK_STATES)])
            for task in tasks:
                task.message_post(body=_("The power of attorney this matter relies on (%(poa)s) %(what)s. "
                                         "Record a valid one before the next step.", poa=poa.name, what=what))
                user = task.lawyer_id if task.lawyer_id.active else self.env["res.users"]
                if user:
                    task.activity_schedule(
                        activity_type_id=activity_type.id if activity_type else False,
                        summary=_("Power of attorney no longer valid — %s", poa.name),
                        user_id=user.id, date_deadline=fields.Date.context_today(self))

    def _ldm_close_reminders(self):
        close_activities(self, "ldm_activity_poa_expiry")

    def action_ldm_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_task")
        action.update({"name": _("Matters relying on %s", self.name), "domain": [("poa_id", "=", self.id)],
                       "context": {"default_poa_id": self.id}})
        return action


class LegalCompany(models.Model):
    _inherit = "legal.company"

    def action_ldm_view_poas(self):
        """Who can act for this client today: its live powers of attorney, with
        the bodies they are valid before and the agents they name."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_poa")
        action.update({
            "name": _("Powers of attorney of %s", self.name),
            "domain": [("principal_company_id", "=", self.id)],
            "context": {"default_principal_company_id": self.id, "search_default_filter_can_act": 1},
        })
        return action


class LegalTask(models.Model):
    _inherit = "legal.task"

    ldm_poa_state = fields.Selection(related="poa_id.state", string="Power of attorney status")

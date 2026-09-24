# -*- coding: utf-8 -*-
"""Recurring obligations of a client (legal.obligation): the annual tax
return, the monthly social-security contribution, the yearly chamber ID
renewal. Each due date opens a matter of the chosen type ``lead_days`` before
it, once per period, and the next due date rolls forward."""
import calendar as pycalendar
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class LegalObligation(models.Model):
    _inherit = "legal.obligation"

    department_id = fields.Many2one(related="template_id.department_id", string="Body")
    lawyer_id = fields.Many2one("res.users", string="Responsible",
                                help="Who the matters are opened for. Empty: the client's responsible.")
    last_period_date = fields.Date(string="Last period opened", readonly=True, copy=False,
                                   help="The due date of the last period for which a matter was opened.")
    open_on = fields.Date(string="Opens on", compute="_compute_open_on",
                          help="The day the matter for the next due date is opened.")
    note = fields.Text(string="Note")
    task_count = fields.Integer(string="Matters", compute="_compute_task_count")

    @api.constrains("month", "day", "recurrence", "lead_days")
    def _check_schedule(self):
        for obligation in self:
            if not 1 <= (obligation.day or 0) <= 31:
                raise ValidationError(_("The day of an obligation must be between 1 and 31."))
            if obligation.recurrence == "yearly" and not 1 <= (obligation.month or 0) <= 12:
                raise ValidationError(_("The month of a yearly obligation must be between 1 and 12."))
            if (obligation.lead_days or 0) < 0:
                raise ValidationError(_("The matter cannot be opened after the due date."))

    @api.depends("next_date", "lead_days")
    def _compute_open_on(self):
        for obligation in self:
            obligation.open_on = (obligation.next_date - relativedelta(days=obligation.lead_days or 0)
                                  if obligation.next_date else False)

    def _compute_task_count(self):
        groups = self.env["legal.task"]._read_group([("ldm_obligation_id", "in", self.ids)],
                                                    ["ldm_obligation_id"], ["__count"])
        counts = {obligation.id: count for obligation, count in groups}
        for obligation in self:
            obligation.task_count = counts.get(obligation.id, 0)

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    @staticmethod
    def _ldm_on_day(year, month, day):
        """``day`` of that month, the last day when the month is shorter."""
        return date(year, month, min(day, pycalendar.monthrange(year, month)[1]))

    def _ldm_occurrence_on_or_after(self, start):
        """First due date on or after ``start``."""
        self.ensure_one()
        day = self.day or 1
        if self.recurrence == "monthly":
            candidate = self._ldm_on_day(start.year, start.month, day)
            if candidate < start:
                following = start + relativedelta(months=1)
                candidate = self._ldm_on_day(following.year, following.month, day)
            return candidate
        month = self.month or 1
        candidate = self._ldm_on_day(start.year, month, day)
        if candidate < start:
            candidate = self._ldm_on_day(start.year + 1, month, day)
        return candidate

    def _ldm_following(self, due):
        """The due date after ``due``."""
        self.ensure_one()
        if self.recurrence == "monthly":
            following = due + relativedelta(months=1)
            return self._ldm_on_day(following.year, following.month, self.day or 1)
        return self._ldm_on_day(due.year + 1, self.month or 1, self.day or 1)

    @api.onchange("recurrence", "month", "day")
    def _onchange_schedule(self):
        if self.day and (self.recurrence == "monthly" or self.month):
            with_valid = 1 <= self.day <= 31 and (self.recurrence == "monthly" or 1 <= self.month <= 12)
            if with_valid:
                self.next_date = self._ldm_occurrence_on_or_after(fields.Date.context_today(self))

    @api.model_create_multi
    def create(self, vals_list):
        obligations = super().create(vals_list)
        today = fields.Date.context_today(self)
        for obligation in obligations.filtered(lambda o: not o.next_date):
            obligation.next_date = obligation._ldm_occurrence_on_or_after(today)
        return obligations

    # ------------------------------------------------------------------
    # Opening the matter of a period
    # ------------------------------------------------------------------
    def _ldm_responsible(self):
        self.ensure_one()
        user = self.lawyer_id or self.template_id.lawyer_id or self.legal_company_id.lawyer_id
        return user if user and user.active and not user.share else self.env["res.users"]

    def _ldm_open_period(self):
        """Open the matter for the current ``next_date`` unless one exists for
        that period, then roll ``next_date`` forward. Returns the matter."""
        self.ensure_one()
        Task = self.env["legal.task"].sudo().with_context(active_test=False)
        period = self.next_date
        task = Task.search([("ldm_obligation_id", "=", self.id), ("ldm_obligation_period", "=", period)], limit=1)
        if not task:
            user = self._ldm_responsible()
            creator = self.env["legal.task"].with_user(user) if user else self.env["legal.task"].sudo()
            values = {
                "template_id": self.template_id.id,
                "legal_company_id": self.legal_company_id.id,
                "name": _("%(obligation)s — due %(date)s", obligation=self.name,
                          date=format_date(self.env, period)),
                "key_date": period,
                "company_id": self.company_id.id or self.env.company.id,
            }
            if user:
                values["lawyer_id"] = user.id
            task_id = creator.with_company(self.company_id or self.env.company).create_from_template(values)
            task = Task.browse(task_id)
            root = self.env.ref("base.user_root")
            if root in task.lawyer_ids and task.lawyer_id != root:
                task.lawyer_ids = [(3, root.id)]
            task.write({"ldm_obligation_id": self.id, "ldm_obligation_period": period})
            task.message_post(body=_("Opened for the recurring obligation “%(obligation)s”, due %(date)s.",
                                     obligation=self.name, date=format_date(self.env, period)),
                              subtype_xmlid="mail.mt_note")
        self.sudo().write({"last_task_id": task.id, "last_period_date": period,
                           "next_date": self._ldm_following(period)})
        return task

    @api.model
    def _cron_ldm_open_obligations(self):
        """Daily: open the matter of every obligation whose opening day has come.
        One period per obligation per run; a period is never opened twice."""
        today = fields.Date.context_today(self)
        for obligation in self.sudo().search([("active", "=", True), ("template_id", "!=", False),
                                             ("next_date", "!=", False)]):
            if obligation.next_date - relativedelta(days=obligation.lead_days or 0) <= today:
                obligation._ldm_open_period()
        return True

    def action_ldm_open_now(self):
        """Open the matter of the next period now, without waiting for the lead time."""
        self.ensure_one()
        if not self.env.user.has_group("legal_department_management.group_legal_user"):
            raise UserError(_("Only a lawyer can open a matter for an obligation."))
        if not self.template_id:
            raise UserError(_("Choose the type of matter this obligation opens first."))
        if not self.next_date:
            raise UserError(_("Set the next due date first."))
        task = self._ldm_open_period()
        return {"type": "ir.actions.act_window", "res_model": "legal.task", "res_id": task.id,
                "view_mode": "form", "target": "current"}

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_task")
        action.update({"name": _("Matters for %s", self.name), "domain": [("ldm_obligation_id", "=", self.id)],
                       "context": {"search_default_filter_open": 0}})
        return action

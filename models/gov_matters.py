# -*- coding: utf-8 -*-
"""Government transactions on the matter: how long the file has been at the
body against the time it usually takes, counter visits, and the reminders for
documents that expire."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from .ldm_reminders import ldm_day, ldm_key
from .legal_task import CLOSED_STATES, OPEN_STATES

OUTSIDE = ("body", "verification")


class LegalTask(models.Model):
    _inherit = "legal.task"

    ldm_target_days = fields.Integer(
        string="Usual answer time", compute="_compute_ldm_target_days",
        help="Working days the body usually takes: from the matter type, else from the body.")
    ldm_body_due_date = fields.Date(
        string="Answer expected by", compute="_compute_ldm_body_due_date", store=True, index=True,
        help="The date the body should have answered, counted in working days on its calendar from the day the file was submitted.")
    ldm_past_target = fields.Boolean(
        string="At the body past target", compute="_compute_ldm_past_target", search="_search_ldm_past_target")
    ldm_open_visit_count = fields.Integer(string="Open visits", compute="_compute_ldm_open_visit_count")
    ldm_obligation_id = fields.Many2one("legal.obligation", string="Opened for obligation", index=True,
                                        ondelete="set null", copy=False, readonly=True)
    ldm_obligation_period = fields.Date(string="Obligation due on", copy=False, readonly=True)

    @api.depends("template_id.target_days", "department_id.target_days")
    def _compute_ldm_target_days(self):
        for task in self:
            task.ldm_target_days = task.template_id.target_days or task.department_id.target_days or 0

    @api.depends("date_submitted", "waiting_on", "template_id.target_days", "department_id.target_days",
                 "department_id.resource_calendar_id", "kind")
    def _compute_ldm_body_due_date(self):
        for task in self:
            days = task.template_id.target_days or task.department_id.target_days
            if task.kind != "government" or not task.date_submitted or not days or task.waiting_on not in OUTSIDE:
                task.ldm_body_due_date = False
                continue
            calendar = task.department_id._ldm_calendar() if task.department_id else task.company_id._ldm_calendar()
            task.ldm_body_due_date = task.company_id.ldm_add_working_days(task.date_submitted, days, calendar)

    @api.depends_context("tz")
    @api.depends("ldm_body_due_date", "state")
    def _compute_ldm_past_target(self):
        today = fields.Date.context_today(self)
        for task in self:
            task.ldm_past_target = bool(task.state in OPEN_STATES and task.ldm_body_due_date
                                        and task.ldm_body_due_date < today)

    def _search_ldm_past_target(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented
        domain = Domain(self._ldm_past_target_domain())
        return domain if (operator == "=") == value else ~domain

    @api.model
    def _ldm_past_target_domain(self):
        """Open government matters whose file has been at the body longer than
        the body usually takes (working days on the body's calendar). Used by the
        "At the body past target" filter and by the managers' band on My Day."""
        today = fields.Date.context_today(self)
        return [("kind", "=", "government"), ("state", "in", list(OPEN_STATES)),
                ("waiting_on", "in", list(OUTSIDE)), ("ldm_body_due_date", "!=", False),
                ("ldm_body_due_date", "<", fields.Date.to_string(today))]

    def _compute_ldm_open_visit_count(self):
        groups = self.env["legal.task.step"]._read_group(
            [("task_id", "in", self.ids), ("is_visit", "=", True), ("state", "=", "todo")], ["task_id"], ["__count"])
        counts = {task.id: count for task, count in groups}
        for task in self:
            task.ldm_open_visit_count = counts.get(task.id, 0)

    # ------------------------------------------------------------------
    # Counter visits
    # ------------------------------------------------------------------
    def action_ldm_log_visit(self):
        """Log a counter visit on the matter's next open visit, or an unplanned one."""
        self.ensure_one()
        if self.state in CLOSED_STATES:
            raise UserError(_("%s is closed; reopen it before logging a visit.", self.display_name))
        step = self.step_ids.filtered(lambda s: s.is_visit and s.state == "todo").sorted(
            lambda s: (s.date_due or fields.Date.today(), s.sequence, s.id))[:1]
        if step:
            return step.action_ldm_log_visit()
        return self.env["legal.visit.wizard"]._ldm_open({"default_task_id": self.id})

    # ------------------------------------------------------------------
    # Reminders
    # ------------------------------------------------------------------
    @api.model
    def _ldm_reminder_items(self, company, today, horizon):
        """Add documents collected for a matter that expire within the reminder
        window (or already have), so the responsible renews them in time."""
        items = super()._ldm_reminder_items(company, today, horizon)
        documents = self.env["legal.task.document"].search([
            ("company_id", "=", company.id),
            ("state", "in", ("received", "awaiting_verification", "verified", "expired")),
            ("expiry_date", "!=", False), ("expiry_date", "<=", horizon),
            ("task_id.state", "in", list(OPEN_STATES)),
        ])
        for doc in documents:
            user = doc.task_id.lawyer_id
            env = self._ldm_reminder_env(user)
            summary = env._("Document expires on %(date)s: %(name)s — %(number)s",
                            date=ldm_day(env, doc.expiry_date, today), name=doc.name,
                            number=doc.task_id.task_number)
            items.append((doc.task_id, user, doc.expiry_date, summary, "ldm_activity_expiry", ldm_key(doc)))
        return items

    @api.model
    def _ldm_run_reminders(self):
        result = super()._ldm_run_reminders()
        self.env["legal.company"]._ldm_run_company_reminders()
        return result


class LegalTaskStep(models.Model):
    _inherit = "legal.task.step"

    visit_waiting_for = fields.Char(string="The body is waiting for")

    def action_ldm_log_visit(self):
        """Open the counter-visit dialog for this step (SPEC 14.4: a visit is a step)."""
        self.ensure_one()
        if not self.is_visit:
            raise UserError(_("“%s” is not a visit to a body.", self.name))
        if self.state != "todo":
            raise UserError(_("“%s” is already done.", self.name))
        return self.env["legal.visit.wizard"]._ldm_open({"default_step_id": self.id, "default_task_id": self.task_id.id})


class LegalExpenseCategory(models.Model):
    _inherit = "legal.expense.category"

    @api.model
    def _ldm_government_fee(self):
        """The "government fee" category. The money stream seeds the categories;
        this finds it by xmlid, then by code, and creates it only if missing."""
        for xmlid in ("legal_department_management.ldm_expense_category_government_fee",
                      "legal_department_management.expense_category_government_fee"):
            category = self.env.ref(xmlid, raise_if_not_found=False)
            if category:
                return category
        Category = self.sudo().with_context(active_test=False)
        category = Category.search([("code", "in", ("government_fee", "gov_fee", "GOV"))], limit=1)
        if not category:
            category = Category.create({"name": "Government fee", "code": "government_fee",
                                        "recoverable_default": True})
        return category.sudo(False)

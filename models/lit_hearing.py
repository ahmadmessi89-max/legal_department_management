# -*- coding: utf-8 -*-
"""Court sessions: the outcome dialog, the licence-class and substitution
checks, and the calendar's shaded non-working days."""
from odoo import _, api, fields, models

from .ldm_reminders import ldm_key, ldm_key_matches
from .lit_rules import ldm_date

from .lit_report import _time_label

# Trainee lawyers may not appear before these courts (Advocacy Law and the Bar
# Council's classes of appearance rights; SPEC 14.6).
TRAINEE_BARRED = ("appeal", "cassation", "felony")


class LegalHearing(models.Model):
    _inherit = "legal.hearing"

    lawyer_id = fields.Many2one(related="task_id.lawyer_id", string="Responsible", store=True, index=True)
    court_case_number = fields.Char(related="task_id.court_case_number", string="Case number")
    task_kind = fields.Selection(related="task_id.kind", string="Kind of matter")
    poa_id = fields.Many2one(related="task_id.poa_id", string="Power of attorney")
    previous_hearing_id = fields.Many2one("legal.hearing", string="Previous session",
                                          compute="_compute_previous_hearing")
    licence_warning = fields.Char(string="Licence warning", compute="_compute_warnings")
    needs_substitution_letter = fields.Boolean(
        string="Needs a substitution letter", compute="_compute_warnings",
        help="The person attending is not an agent under the matter's power of attorney, "
        "so they appear by a substitution letter (كتاب إنابة).")
    substitution_warning = fields.Char(string="Substitution warning", compute="_compute_warnings")
    date_warning = fields.Char(string="Date warning", compute="_compute_warnings")

    @api.depends("date", "time", "kind", "task_id.task_number", "task_id.legal_company_id", "department_id")
    @api.depends_context("lang", "ldm_hearing_title")
    def _compute_display_name(self):
        """Elsewhere: date, time and matter number. On the calendar, where the
        date is already the cell: time, client and court."""
        calendar = self.env.context.get("ldm_hearing_title") == "calendar"
        for hearing in self:
            if calendar:
                parts = [_time_label(hearing.time), hearing.task_id.legal_company_id.name or "",
                         hearing.department_id.name or ""]
            else:
                parts = [ldm_date(self.env, hearing.date) if hearing.date else "", _time_label(hearing.time),
                         hearing.task_id.task_number or ""]
            hearing.display_name = " · ".join(p for p in parts if p)

    def _compute_previous_hearing(self):
        previous = {h.next_hearing_id.id: h for h in self.search([("next_hearing_id", "in", self.ids)])}
        for hearing in self:
            hearing.previous_hearing_id = previous.get(hearing.id, False)

    @api.depends("attending_user_id.ldm_licence_class", "department_id.court_degree", "substitute_partner_id",
                 "task_id.poa_id.agent_user_ids", "task_id.poa_id.agent_partner_ids",
                 "task_id.poa_id.substitution_allowed", "date", "state")
    @api.depends_context("lang")
    def _compute_warnings(self):
        for hearing in self:
            hearing.licence_warning = hearing._ldm_licence_warning() or False
            letter = hearing._ldm_needs_letter()
            hearing.needs_substitution_letter = letter
            poa = hearing.task_id.poa_id
            hearing.substitution_warning = _(
                "The power of attorney %s does not let the agent delegate, so a substitution letter under it "
                "is not valid.", poa.display_name) if letter and poa and not poa.substitution_allowed else False
            hearing.date_warning = hearing._ldm_date_warning(hearing.date) if hearing.state == "planned" else False

    def _ldm_licence_warning(self):
        self.ensure_one()
        user = self.attending_user_id
        degree = self.department_id.court_degree
        if user.ldm_licence_class == "trainee" and degree in TRAINEE_BARRED:
            degrees = dict(self.department_id._fields["court_degree"]._description_selection(self.env))
            return _("%(user)s is a trainee lawyer: a trainee may not appear before a %(court)s.",
                     user=user.name, court=degrees[degree].lower())
        return False

    def _ldm_needs_letter(self):
        self.ensure_one()
        poa = self.task_id.poa_id
        if self.substitute_partner_id:
            return not (poa and self.substitute_partner_id in poa.agent_partner_ids)
        if poa and self.attending_user_id:
            return self.attending_user_id not in poa.agent_user_ids
        return False

    def _ldm_calendar(self):
        self.ensure_one()
        court = self.department_id or self.task_id.department_id
        return court._ldm_calendar() if court else (self.company_id or self.env.company)._ldm_calendar()

    def _ldm_date_warning(self, day):
        """A sentence when ``day`` is not a working day at this session's court."""
        self.ensure_one()
        if not day:
            return False
        company = self.company_id or self.task_id.company_id or self.env.company
        if company.ldm_is_working_day(day, self._ldm_calendar()):
            return False
        return _("%s is not a working day at this court.", ldm_date(self.env, day))

    @api.onchange("attending_user_id", "department_id")
    def _onchange_licence_class(self):
        warning = self._ldm_licence_warning()
        if warning:
            return {"warning": {"title": _("Licence class"), "message": warning}}
        return None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def write(self, vals):
        leaving = self.browse()
        if vals.get("state") and vals["state"] != "planned":
            leaving = self.filtered(lambda h: h.state == "planned")
        result = super().write(vals)
        if leaving:
            leaving._ldm_close_reminders()
        return result

    def _ldm_close_reminders(self):
        """Close the reminders the daily run opened for these sessions: found by
        their key (the session), and, for an activity written before keys
        existed, by the session's date in its text."""
        activity_type = self.env.ref("legal_department_management.ldm_activity_session", raise_if_not_found=False)
        if not activity_type:
            return
        for hearing in self:
            key = ldm_key(hearing)
            marker = fields.Date.to_string(hearing.date)
            activities = hearing.task_id.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type and (
                    ldm_key_matches(a.ldm_reminder_key, key)
                    or (not a.ldm_reminder_key and marker in (a.summary or ""))))
            if activities:
                activities.sudo().action_feedback(feedback=_("Session recorded."))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_ldm_record_outcome(self):
        """Interface (SPEC 5.8): the session-outcome dialog."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Record the session"),
            "res_model": "legal.hearing.outcome.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_hearing_id": self.id},
        }

    def action_ldm_print_substitution_letter(self):
        return self.env.ref("legal_department_management.action_report_ldm_substitution").report_action(self)

    # ------------------------------------------------------------------
    # Calendar view: shade weekends and holidays of the legal calendar
    # ------------------------------------------------------------------
    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env["legal.deadline"].get_unusual_days(date_from, date_to)

# -*- coding: utf-8 -*-
"""Record what happened at a court session, in one step and one transaction:
the session, the next session, what is needed before it, a judgment with its
challenge deadlines, or the period an outcome starts (a case left for review,
suspended, stayed or interrupted)."""
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import format_date

from ..models.base_litigation import HEARING_OUTCOMES
from ..models.legal_department import COURT_DEGREES
from ..models.lit_rules import LAW_OF_BRANCH
from ..models.lit_rules import ldm_user_is

MAIN_OUTCOMES = [
    ("adjourned", "Adjourned"),
    ("pleading", "Pleadings exchanged"),
    ("reserved", "Reserved for judgment"),
    ("judgment", "Judgment given"),
    ("expert", "Expert appointed"),
    ("left_for_review", "Left for review"),
    ("more", "Something else"),
]
MORE_OUTCOMES = [pair for pair in HEARING_OUTCOMES if pair[0] not in dict(MAIN_OUTCOMES)]
# Outcomes after which the court sits again on a date it fixes.
NEEDS_NEXT = ("adjourned", "pleading", "reserved", "expert", "witnesses")
# Outcomes after which there is no next session to fix.
NO_NEXT = ("judgment", "left_for_review", "suspended", "stayed", "interrupted", "struck_out", "settled")
ATTENDANCE = [
    ("present", "We attended"),
    ("we_absent", "We were absent"),
    ("opponent_absent", "The other side was absent"),
    ("both_absent", "Both sides absent"),
]
RESULTS = [("for", "In our favour"), ("against", "Against us"), ("partial", "Partly in our favour"),
           ("other", "Other")]
LAWS = [("civil", "Civil"), ("criminal", "Criminal"), ("administrative", "Administrative"),
        ("labour", "Labour"), ("execution", "Execution"), ("other", "Other")]
# An agreed suspension lasts at most three months (Civil Procedure Law Art. 82).
SUSPENSION_MONTHS = 3


class LegalHearingOutcomeWizard(models.TransientModel):
    _name = "legal.hearing.outcome.wizard"
    _description = "Record a court session"

    hearing_id = fields.Many2one("legal.hearing", string="Session", required=True, ondelete="cascade")
    task_id = fields.Many2one(related="hearing_id.task_id", string="Matter")
    company_id = fields.Many2one(related="hearing_id.task_id.company_id", string="Company")
    currency_id = fields.Many2one(related="hearing_id.task_id.currency_id", string="Currency")
    session_label = fields.Char(string="Session summary", compute="_compute_session_label")

    main_outcome = fields.Selection(MAIN_OUTCOMES, string="What happened", required=True, default="adjourned")
    more_outcome = fields.Selection(MORE_OUTCOMES, string="Other outcome")
    outcome = fields.Selection(HEARING_OUTCOMES, string="Outcome", compute="_compute_outcome")
    attendance = fields.Selection(ATTENDANCE, string="Attendance", default="present")
    show_next = fields.Boolean(compute="_compute_outcome")
    next_required = fields.Boolean(compute="_compute_outcome")
    next_date = fields.Date(string="Next session")
    next_time = fields.Float(string="At")
    next_date_warning = fields.Char(compute="_compute_next_date_warning")
    needed_before = fields.Char(string="Needed before it",
                                help="What must be ready for the next session. It becomes a to-do for the "
                                "responsible lawyer a few working days before the session.")
    needed_days = fields.Integer(string="Working days before", compute="_compute_needed_days", store=True,
                                 readonly=False, precompute=True)
    note = fields.Text(string="Note")

    # Judgment
    judgment_date = fields.Date(string="Judgment date", compute="_compute_from_hearing", store=True,
                                readonly=False, precompute=True)
    result = fields.Selection(RESULTS, string="Result")
    law = fields.Selection(LAWS, string="Law", compute="_compute_from_hearing", store=True, readonly=False,
                           precompute=True)
    court_degree = fields.Selection(COURT_DEGREES, string="Court degree", compute="_compute_from_hearing",
                                    store=True, readonly=False, precompute=True)
    in_absentia = fields.Boolean(string="Given in absence", compute="_compute_presence", store=True,
                                 readonly=False, precompute=True)
    pronounced_in_presence = fields.Boolean(string="Pronounced in our presence", compute="_compute_presence",
                                            store=True, readonly=False, precompute=True)
    amount_awarded = fields.Monetary(string="Amount awarded", currency_field="currency_id")
    notified_date = fields.Date(string="Notified on",
                                help="The date the judgment was served (التبليغ), if it already was. Most "
                                "challenge periods count from the next day.")
    deadline_preview = fields.Html(string="Deadlines", compute="_compute_deadline_preview", sanitize=False)

    # A period that the outcome starts
    rule_id = fields.Many2one("legal.appeal.rule", string="Period", compute="_compute_rule", store=True,
                              readonly=False, precompute=True)
    add_period = fields.Boolean(string="Add this period", default=True)
    period_start = fields.Date(string="Counted from", compute="_compute_rule", store=True, readonly=False,
                               precompute=True,
                               help="For a suspension: the day the agreed suspension ends. The case must be "
                               "resumed within the period after it.")
    period_preview = fields.Char(string="Act by", compute="_compute_period_preview")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("hearing_id")
    @api.depends_context("lang")
    def _compute_session_label(self):
        for wizard in self:
            hearing = wizard.hearing_id
            parts = [format_date(self.env, hearing.date, date_format="EEEE d MMMM y") if hearing.date else "",
                     hearing.department_id.name or "", hearing.task_id.display_name or ""]
            wizard.session_label = " · ".join(p for p in parts if p)

    @api.depends("main_outcome", "more_outcome")
    def _compute_outcome(self):
        for wizard in self:
            outcome = wizard.more_outcome if wizard.main_outcome == "more" else wizard.main_outcome
            wizard.outcome = outcome or False
            wizard.show_next = outcome not in NO_NEXT
            wizard.next_required = outcome in NEEDS_NEXT

    @api.depends("next_date", "hearing_id")
    @api.depends_context("lang")
    def _compute_next_date_warning(self):
        for wizard in self:
            wizard.next_date_warning = wizard.hearing_id._ldm_date_warning(wizard.next_date) if wizard.hearing_id else False

    @api.depends("hearing_id")
    def _compute_needed_days(self):
        for wizard in self:
            wizard.needed_days = wizard.hearing_id.task_id.company_id.ldm_reminder_days or 2

    @api.depends("hearing_id")
    def _compute_from_hearing(self):
        for wizard in self:
            hearing = wizard.hearing_id
            task = hearing.task_id
            wizard.judgment_date = hearing.date
            wizard.law = LAW_OF_BRANCH.get(task.law_branch or "civil", "civil")
            wizard.court_degree = hearing.department_id.court_degree or task.department_id.court_degree or False

    @api.depends("attendance")
    def _compute_presence(self):
        for wizard in self:
            wizard.in_absentia = wizard.attendance in ("we_absent", "both_absent")
            wizard.pronounced_in_presence = wizard.attendance in ("present", "opponent_absent")

    @api.depends("outcome", "hearing_id")
    def _compute_rule(self):
        Rule = self.env["legal.appeal.rule"]
        for wizard in self:
            rule = Rule.search([("trigger_outcome", "=", wizard.outcome)], limit=1) if wizard.outcome else Rule
            wizard.rule_id = rule
            start = wizard.hearing_id.date
            if wizard.outcome == "suspended" and start:
                start = start + relativedelta(months=SUSPENSION_MONTHS)
            wizard.period_start = start

    @api.depends("rule_id", "period_start", "hearing_id")
    @api.depends_context("lang")
    def _compute_period_preview(self):
        for wizard in self:
            if not (wizard.rule_id and wizard.period_start and wizard.hearing_id):
                wizard.period_preview = False
                continue
            safe, legal = wizard.rule_id._ldm_dates(wizard._ldm_company(), wizard.period_start,
                                                    wizard.hearing_id._ldm_calendar())
            wizard.period_preview = wizard._ldm_dates_label(safe, legal)

    @api.depends("outcome", "judgment_date", "law", "court_degree", "in_absentia", "pronounced_in_presence",
                 "notified_date", "result", "hearing_id")
    @api.depends_context("lang")
    def _compute_deadline_preview(self):
        """The challenge periods the judgment will open, so the lawyer sees
        them before saving."""
        rules = self.env["legal.appeal.rule"].search([("from_judgment", "=", True)])
        for wizard in self:
            if wizard.outcome != "judgment" or not wizard.hearing_id or not wizard.judgment_date:
                wizard.deadline_preview = False
                continue
            probe = wizard._ldm_judgment_probe()
            lines = []
            for rule in rules.filtered(lambda r: r._ldm_matches(probe)):
                event = rule._ldm_event_date(probe)
                if event:
                    safe, legal = rule._ldm_dates(wizard._ldm_company(), event, wizard.hearing_id._ldm_calendar(),
                                                  wizard.judgment_date)
                    when = wizard._ldm_dates_label(safe, legal)
                else:
                    when = _("counted once the notification date is entered")
                lines.append(Markup("<li><b>%s</b> — %s</li>") % (rule.name, when))
            if not lines:
                wizard.deadline_preview = Markup("<p class='text-muted mb-0'>%s</p>") % _(
                    "No statutory period applies to this judgment.")
            else:
                wizard.deadline_preview = Markup("<ul class='mb-0 ps-3'>%s</ul>") % Markup("").join(lines)

    def _ldm_company(self):
        return self.hearing_id.task_id.company_id or self.env.company

    def _ldm_dates_label(self, safe, legal):
        if not safe:
            return ""
        if legal and legal != safe:
            return _("act by %(safe)s · legal last day %(legal)s", safe=format_date(self.env, safe),
                     legal=format_date(self.env, legal))
        return _("act by %s", format_date(self.env, safe))

    def _ldm_judgment_probe(self):
        """An unsaved judgment carrying the dialog's answers, to match rules."""
        return self.env["legal.judgment"].new({
            "task_id": self.hearing_id.task_id.id,
            "date": self.judgment_date,
            "law": self.law or "civil",
            "court_degree": self.court_degree,
            "in_absentia": self.in_absentia,
            "pronounced_in_presence": self.pronounced_in_presence,
            "notified_date": self.notified_date,
            "result": self.result,
            "department_id": self.hearing_id.department_id.id,
        })

    @api.onchange("main_outcome")
    def _onchange_main_outcome(self):
        if self.main_outcome != "more":
            self.more_outcome = False

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def action_confirm(self):
        self.ensure_one()
        hearing = self.hearing_id
        user = self.env.user
        if not ldm_user_is(self.env, "group_ldm_clerk"):
            raise AccessError(_("Only the legal team can record a court session."))
        hearing.check_access("write")
        outcome = self.outcome
        if not outcome:
            raise UserError(_("Choose what happened at the session."))
        if hearing.state != "planned":
            raise UserError(_("This session is already recorded. Open it to change what was written."))
        if outcome in NEEDS_NEXT and not self.next_date:
            raise UserError(_("Give the date of the next session."))
        if self.next_date and hearing.date and self.next_date <= hearing.date:
            raise UserError(_("The next session must come after this one."))
        if outcome == "judgment":
            if not ldm_user_is(self.env, "group_legal_user"):
                raise AccessError(_("Only a lawyer can record a judgment."))
            if not self.judgment_date:
                raise UserError(_("Give the date of the judgment."))

        task = hearing.task_id
        lines = [_("Court session of %(date)s: %(outcome)s.", date=format_date(self.env, hearing.date),
                   outcome=self._ldm_label("outcome", outcome))]
        if self.attendance and self.attendance != "present":
            lines.append(self._ldm_label("attendance", self.attendance) + ".")

        # 1. The next session.
        next_hearing = self.env["legal.hearing"]
        if self.next_date and outcome not in NO_NEXT:
            next_hearing = next_hearing.create({
                "task_id": task.id,
                "kind": hearing.kind,
                "date": self.next_date,
                "time": self.next_time,
                "department_id": hearing.department_id.id,
                "court_room": hearing.court_room,
                "attending_user_id": hearing.attending_user_id.id,
                "substitute_partner_id": hearing.substitute_partner_id.id,
            })
            lines.append(_("Next session: %s.", format_date(self.env, self.next_date)))

        # 2. The session itself.
        values = {"state": "held", "outcome": outcome, "attendance": self.attendance,
                  "needed_before": self.needed_before or False}
        if next_hearing:
            values["next_hearing_id"] = next_hearing.id
        if self.note:
            values["outcome_note"] = self.note
        hearing.write(values)

        # 3. What is needed before the next session: a to-do for the responsible.
        if self.needed_before and next_hearing:
            company = task.company_id
            due = company.ldm_add_working_days(self.next_date, -abs(self.needed_days or 0),
                                               next_hearing._ldm_calendar()) if self.needed_days else self.next_date
            task.activity_schedule(
                "mail.mail_activity_data_todo", date_deadline=max(due, fields.Date.context_today(self)),
                summary=self.needed_before, user_id=(task.lawyer_id or user).id,
                note=_("Needed before the court session of %s.", format_date(self.env, self.next_date)))
            lines.append(_("Needed before it: %s.", self.needed_before))

        # 4. A judgment and its challenge deadlines.
        judgment = self.env["legal.judgment"]
        if outcome == "judgment":
            judgment = judgment.create({
                "task_id": task.id,
                "hearing_id": hearing.id,
                "date": self.judgment_date,
                "department_id": hearing.department_id.id or task.department_id.id,
                "court_degree": self.court_degree,
                "court_stage": task.court_stage,
                "law": self.law or "civil",
                "in_absentia": self.in_absentia,
                "pronounced_in_presence": self.pronounced_in_presence,
                "result": self.result,
                "amount_awarded": self.amount_awarded,
                "notified_date": self.notified_date,
            })
            Deadline = self.env["legal.deadline"]
            lines.append(_("Judgment: %s.", self._ldm_label("result", self.result) if self.result else _("recorded")))
            lines += [Deadline._ldm_describe(d) for d in judgment.deadline_ids.sorted("id")]

        # 5. The period this outcome starts.
        deadline = self.env["legal.deadline"]
        if self.rule_id and self.add_period and outcome not in ("judgment",) and self.period_start:
            deadline = self.env["legal.deadline"].sudo().create({
                "task_id": task.id,
                "rule_id": self.rule_id.id,
                "date_start": self.period_start,
                "source_model": "legal.hearing",
                "source_id": hearing.id,
            }).with_env(self.env)
            lines.append(self.env["legal.deadline"]._ldm_describe(deadline))

        if self.note:
            lines.append(_("Note: %s", self.note))
        task.message_post(body=Markup("<br/>").join(lines), message_type="comment", subtype_xmlid="mail.mt_note")

        message = lines[0] if not next_hearing else _("Recorded. Next session on %s.",
                                                      format_date(self.env, self.next_date))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"type": "success", "message": message, "next": {"type": "ir.actions.act_window_close"}},
        }

    def _ldm_label(self, field, value):
        return dict(self._fields[field]._description_selection(self.env)).get(value, "") if value else ""

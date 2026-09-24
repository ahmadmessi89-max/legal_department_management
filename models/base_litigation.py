# -*- coding: utf-8 -*-
"""Declarations for court sessions, court stages, parties, judgments, statutory
periods, deadlines and holidays. The litigation stream owns their behaviour and
views; the foundation gives every stored compute a working body."""
from odoo import api, fields, models

from .legal_department import COURT_DEGREES
from .legal_ministry import GOVERNORATES

COURT_STAGES = [
    ("first_instance", "First instance"),
    ("appeal", "Appeal"),
    ("cassation", "Cassation"),
    ("execution", "Execution"),
]

HEARING_OUTCOMES = [
    ("adjourned", "Adjourned"),
    ("pleading", "Pleadings exchanged"),
    ("reserved", "Reserved for judgment"),
    ("judgment", "Judgment given"),
    ("left_for_review", "Left for review"),
    ("suspended", "Suspended by agreement"),
    ("stayed", "Stayed pending another question"),
    ("interrupted", "Interrupted"),
    ("expert", "Expert appointed"),
    ("witnesses", "Witnesses heard"),
    ("struck_out", "Struck out"),
    ("settled", "Settled"),
    ("other", "Other"),
]


class LegalHearing(models.Model):
    """A court session or a meeting. Visits to government counters are steps,
    not hearings (SPEC §14.4)."""

    _name = "legal.hearing"
    _description = "Court session"
    _inherit = ["mail.thread"]
    _order = "date desc, time desc, id desc"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    legal_company_id = fields.Many2one(related="task_id.legal_company_id", store=True, string="Client")
    kind = fields.Selection([("hearing", "Court session"), ("meeting", "Meeting")],
                            string="Kind", default="hearing", required=True)
    date = fields.Date(string="Date", required=True, index=True, tracking=True)
    time = fields.Float(string="Time")
    department_id = fields.Many2one("legal.department", string="Court", ondelete="restrict", tracking=True)
    court_room = fields.Char(string="Room")
    purpose = fields.Char(string="Purpose")
    attending_user_id = fields.Many2one("res.users", string="Attended by", index=True, tracking=True)
    substitute_partner_id = fields.Many2one(
        "res.partner", string="Substitute lawyer", ondelete="set null",
        help="An outside lawyer attending by substitution letter (إنابة).")
    state = fields.Selection([("planned", "Planned"), ("held", "Held"), ("cancelled", "Cancelled")],
                             string="Status", default="planned", required=True, index=True, tracking=True)
    attendance = fields.Selection(
        [("present", "We attended"), ("we_absent", "We were absent"),
         ("opponent_absent", "The other side was absent"), ("both_absent", "Both sides absent")],
        string="Attendance")
    outcome = fields.Selection(HEARING_OUTCOMES, string="Outcome", tracking=True)
    outcome_note = fields.Text(string="What happened",
                               groups="legal_department_management.group_ldm_clerk,legal_department_management.group_ldm_auditor")
    next_hearing_id = fields.Many2one("legal.hearing", string="Next session", ondelete="set null")
    needed_before = fields.Char(string="Needed before the next session")
    minutes_attachment_id = fields.Many2one("ir.attachment", string="Minutes", ondelete="set null")

    @api.depends("date", "kind", "task_id.task_number")
    def _compute_display_name(self):
        kinds = dict(self._fields["kind"]._description_selection(self.env))
        for hearing in self:
            parts = [kinds.get(hearing.kind, ""), fields.Date.to_string(hearing.date) if hearing.date else ""]
            if hearing.task_id.task_number:
                parts.append(hearing.task_id.task_number)
            hearing.display_name = " · ".join(p for p in parts if p)


class LegalCourtStage(models.Model):
    """One court stage of a lawsuit: its court and its case number. Moving to
    appeal or cassation adds a line; earlier numbers are never overwritten."""

    _name = "legal.court.stage"
    _description = "Court stage"
    _order = "sequence, id"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    sequence = fields.Integer(default=10)
    stage = fields.Selection(COURT_STAGES, string="Stage", required=True, default="first_instance")
    department_id = fields.Many2one("legal.department", string="Court or execution office", ondelete="restrict")
    case_number = fields.Char(string="Case number")
    case_year = fields.Integer(string="Year")
    date_filed = fields.Date(string="Filed on")
    judgment_id = fields.Many2one("legal.judgment", string="Judgment", ondelete="set null")
    execution_file_number = fields.Char(string="Execution file number")
    notification_date = fields.Date(string="Execution notice served on")


class LegalTaskParty(models.Model):
    _name = "legal.task.party"
    _description = "Party to a matter"
    _order = "sequence, id"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one("res.partner", string="Party", required=True, ondelete="restrict", index=True)
    role = fields.Selection(
        [
            ("plaintiff", "Plaintiff"),
            ("defendant", "Defendant"),
            ("complainant", "Complainant"),
            ("accused", "Accused"),
            ("intervener", "Intervener"),
            ("counterparty", "Counterparty"),
            ("witness", "Witness"),
            ("expert", "Expert"),
            ("other", "Other"),
        ],
        string="Role", default="defendant", required=True)
    is_client_side = fields.Boolean(string="On our side")
    counsel_id = fields.Many2one("res.partner", string="Their lawyer", ondelete="set null")
    note = fields.Char(string="Note")


class LegalAppealRule(models.Model):
    """One statutory period, as data: the period, what starts it, its legal basis
    and how sure we are of it. Nothing about Iraqi deadlines is hard-coded."""

    _name = "legal.appeal.rule"
    _description = "Statutory period"
    _order = "law, sequence, days"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    remedy = fields.Selection(
        [
            ("objection", "Objection to a judgment in absence"),
            ("appeal", "Appeal"),
            ("cassation", "Cassation"),
            ("cassation_decision", "Cassation of a decision"),
            ("correction", "Correction of a cassation decision"),
            ("retrial", "Retrial"),
            ("grievance", "Grievance"),
            ("renewal", "Renewal of a case"),
            ("compliance", "Compliance or payment"),
            ("filing", "Filing"),
            ("other", "Other"),
        ],
        string="Remedy", required=True, default="appeal")
    law = fields.Selection(
        [
            ("civil", "Civil procedure"),
            ("criminal", "Criminal procedure"),
            ("administrative", "Administrative"),
            ("labour", "Labour"),
            ("execution", "Execution"),
            ("tax", "Tax"),
            ("social_security", "Social security"),
            ("other", "Other"),
        ],
        string="Law", required=True, default="civil")
    court_degree = fields.Selection(COURT_DEGREES, string="Judgment of",
                                    help="The degree of the court whose judgment starts this period. Empty: any.")
    days = fields.Integer(string="Period", required=True)
    unit = fields.Selection([("days", "Days"), ("months", "Months")], string="Unit", default="days", required=True)
    start_event = fields.Selection(
        [
            ("notification", "Day after notification"),
            ("pronouncement", "Day after pronouncement"),
            ("decision", "Day after the decision"),
            ("discovery", "Day after discovery"),
            ("event", "Day after the event"),
            ("hearing_outcome", "Day after a session outcome"),
            ("previous_deadline_end", "When the previous period ends without an answer"),
        ],
        string="Counted from", default="notification", required=True)
    trigger_outcome = fields.Selection(HEARING_OUTCOMES, string="Started by the outcome",
                                       help="For periods that a session outcome starts, e.g. a case left for review.")
    next_rule_id = fields.Many2one("legal.appeal.rule", string="Then", ondelete="set null",
                                   help="The period that starts when this one ends without an answer "
                                   "(silence counts as rejection).")
    max_months = fields.Integer(string="Never later than (months)",
                                help="An absolute cap counted from the decision, e.g. correction of a cassation decision.")
    extends_on_holiday = fields.Boolean(
        string="Moves off a holiday", default=True,
        help="Civil Procedure Law 83 of 1969, Art. 25(2): a period that ends on an official holiday "
        "ends on the next working day.")
    basis = fields.Char(string="Legal basis", translate=True)
    source_url = fields.Char(string="Source")
    verification = fields.Selection(
        [("verified", "Verified in the law's text"), ("secondary", "From a secondary source"), ("unverified", "Not verified")],
        string="Confidence", default="unverified", required=True)
    note = fields.Text(string="Note", translate=True)


class LegalDeadline(models.Model):
    _name = "legal.deadline"
    _description = "Deadline"
    _inherit = ["mail.thread"]
    _order = "date_safe, id"

    name = fields.Char(string="Deadline", required=True, tracking=True)
    task_id = fields.Many2one("legal.task", string="Matter", ondelete="cascade", index=True)
    company_id = fields.Many2one("res.company", string="Company", required=True, index=True,
                                 default=lambda self: self.env.company)
    legal_company_id = fields.Many2one("legal.company", string="Client", index=True, ondelete="cascade")
    kind = fields.Selection(
        [
            ("appeal", "Appeal window"),
            ("statutory", "Statutory period"),
            ("target", "Target date"),
            ("renewal", "Renewal"),
            ("expiry", "Expiry"),
            ("reply", "Reply due"),
            ("obligation", "Recurring obligation"),
            ("custom", "Other"),
        ],
        string="Kind", default="custom", required=True, index=True)
    date_start = fields.Date(string="Counted from")
    date_safe = fields.Date(string="Act by", index=True, tracking=True,
                            help="The last day of the period counted in calendar days. Act by this date.")
    date_deadline = fields.Date(string="Legal last day", index=True,
                                help="The last day after moving off a holiday where the law allows it.")
    rule_id = fields.Many2one("legal.appeal.rule", string="Rule", ondelete="restrict")
    judgment_id = fields.Many2one("legal.judgment", string="Judgment", ondelete="cascade", index=True)
    previous_deadline_id = fields.Many2one("legal.deadline", string="Follows", ondelete="set null")
    user_id = fields.Many2one("res.users", string="Responsible", index=True)
    state = fields.Selection(
        [("awaiting_service", "Awaiting notification"), ("open", "Open"), ("done", "Met"),
         ("missed", "Missed"), ("cancelled", "Cancelled")],
        string="Status", default="open", required=True, index=True, tracking=True)
    escalated = fields.Boolean(string="Managers told", readonly=True, copy=False)
    note = fields.Char(string="Note")
    source_model = fields.Char(string="Source model", readonly=True)
    source_id = fields.Many2oneReference(string="Source record", model_field="source_model", readonly=True)
    remaining_days = fields.Integer(string="Days left", compute="_compute_remaining_days")

    @api.depends("date_safe", "state")
    def _compute_remaining_days(self):
        today = fields.Date.context_today(self)
        for deadline in self:
            deadline.remaining_days = (deadline.date_safe - today).days if deadline.date_safe else 0


class LegalJudgment(models.Model):
    _name = "legal.judgment"
    _description = "Judgment"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="task_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="task_id.currency_id")
    date = fields.Date(string="Date of judgment", required=True, tracking=True)
    department_id = fields.Many2one("legal.department", string="Court", ondelete="restrict")
    court_degree = fields.Selection(COURT_DEGREES, string="Court degree")
    court_stage = fields.Selection(COURT_STAGES, string="Stage")
    law = fields.Selection(
        [("civil", "Civil"), ("criminal", "Criminal"), ("administrative", "Administrative"),
         ("labour", "Labour"), ("execution", "Execution"), ("other", "Other")],
        string="Law", default="civil", required=True)
    in_absentia = fields.Boolean(string="Given in absence")
    pronounced_in_presence = fields.Boolean(string="Pronounced in our presence")
    result = fields.Selection(
        [("for", "In our favour"), ("against", "Against us"), ("partial", "Partly in our favour"), ("other", "Other")],
        string="Result", tracking=True)
    summary = fields.Text(string="Summary")
    amount_awarded = fields.Monetary(string="Amount awarded", currency_field="currency_id")
    notified_date = fields.Date(string="Notified on", tracking=True,
                                help="Date the judgment was served (التبليغ). Most periods run from the next day.")
    final_date = fields.Date(string="Final on", help="Date the judgment became final (اكتسب الدرجة القطعية).")
    deadline_ids = fields.One2many("legal.deadline", "judgment_id", string="Deadlines")
    hearing_id = fields.Many2one("legal.hearing", string="Given at session", ondelete="set null")


class LegalHoliday(models.Model):
    """A public holiday the legal manager can enter: Eid dates announced by the
    endowment offices, extra days declared by the Council of Ministers. Synced
    into the legal working calendar by the litigation stream."""

    _name = "legal.holiday"
    _description = "Public holiday"
    _order = "date_from desc"

    name = fields.Char(string="Holiday", required=True)
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    governorate = fields.Selection(GOVERNORATES, string="Only in",
                                   help="Leave empty for a holiday in all of Iraq.")
    estimated = fields.Boolean(string="Estimated date",
                               help="The date is an estimate until the endowment offices announce it.")
    calendar_id = fields.Many2one("resource.calendar", string="Calendar", required=True,
                                  default=lambda self: self.env.company._ldm_calendar())
    leave_id = fields.Many2one("resource.calendar.leaves", string="Calendar entry", readonly=True, ondelete="set null")

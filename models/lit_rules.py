# -*- coding: utf-8 -*-
"""Statutory periods as data: which judgment a period applies to, and how its
dates are counted. The periods themselves are seeded in data/lit_data.xml."""
from odoo import _, api, fields, models

from .legal_department import COURT_DEGREES

# Remedies that challenge a judgment. Their deadlines are "appeal windows"; the
# others (renewing a case, a grievance, a filing) are plain statutory periods.
CHALLENGE_REMEDIES = ("objection", "appeal", "cassation", "cassation_decision", "correction", "retrial")

def ldm_user_is(env, group):
    """True for members of a legal role (``group`` is its xmlid in this module),
    and for the superuser that runs crons and data loading."""
    return env.su or env.user.has_group(f"legal_department_management.{group}")


# The judgment's law, from the matter's branch of law.
LAW_OF_BRANCH = {
    "civil": "civil",
    "commercial": "civil",
    "personal_status": "civil",
    "labour": "labour",
    "criminal": "criminal",
    "administrative": "administrative",
    "other": "other",
}


class LegalCourtDegree(models.Model):
    """The degrees of Iraqi courts as records, so a statutory period can apply
    to several of them (cassation of personal-status judgments runs to the
    same 10 days as final-degree first-instance judgments)."""

    _name = "legal.court.degree"
    _description = "Court degree"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Selection(COURT_DEGREES, string="Degree", required=True)
    sequence = fields.Integer(default=10)

    _code_uniq = models.Constraint("UNIQUE(code)", "Each court degree exists once.")


class LegalAppealRule(models.Model):
    _inherit = "legal.appeal.rule"

    degree_ids = fields.Many2many(
        "legal.court.degree", "legal_appeal_rule_degree_rel", "rule_id", "degree_id", string="Judgments of",
        help="The courts whose judgments start this period. Leave empty for any court.")
    judgment_presence = fields.Selection(
        [("any", "Any judgment"), ("absentia", "Judgments given in absence"),
         ("presence", "Judgments given in presence")],
        string="Applies to", default="any", required=True)
    from_judgment = fields.Boolean(
        string="Proposed from a judgment",
        help="Recording a judgment of this law and court degree creates this deadline by itself. "
        "Other periods are added by hand, by a session outcome or by the period before them.")
    peremptory = fields.Boolean(
        string="Cannot be extended", default=True,
        help="Missing the period forfeits the right, and the court rejects a late challenge on its own "
        "motion (Civil Procedure Law 83 of 1969, Art. 171).")
    period_label = fields.Char(string="Length", compute="_compute_period_label")
    deadline_count = fields.Integer(string="Deadlines", compute="_compute_deadline_count")

    @api.depends_context("lang")
    @api.depends("days", "unit")
    def _compute_period_label(self):
        for rule in self:
            if rule.unit == "months":
                rule.period_label = _("%s months", rule.days)
            else:
                rule.period_label = _("%s days", rule.days)

    def _compute_deadline_count(self):
        counts = dict(self.env["legal.deadline"]._read_group(
            [("rule_id", "in", self.ids)], ["rule_id"], ["__count"]))
        for rule in self:
            rule.deadline_count = counts.get(rule, 0)

    @api.depends("code", "name")
    def _compute_display_name(self):
        for rule in self:
            rule.display_name = f"{rule.code} · {rule.name}" if rule.code else (rule.name or "")

    # ------------------------------------------------------------------
    # Matching and counting
    # ------------------------------------------------------------------
    def _ldm_matches(self, judgment):
        """True when this period applies to ``judgment``: same law, a matching
        court degree (none on the rule means any), and presence or absence."""
        self.ensure_one()
        if self.law != judgment.law:
            return False
        degrees = set(self.degree_ids.mapped("code"))
        if self.court_degree:
            degrees.add(self.court_degree)
        if degrees and judgment.court_degree not in degrees:
            return False
        if self.judgment_presence == "absentia" and not judgment.in_absentia:
            return False
        if self.judgment_presence == "presence" and judgment.in_absentia:
            return False
        return True

    def _ldm_event_date(self, judgment):
        """The day the period counts from for ``judgment``. A criminal judgment
        pronounced in our presence counts from the pronouncement (Criminal
        Procedure Law Art. 252); everything else waits for the notification.
        False means the period cannot start yet."""
        self.ensure_one()
        if self.start_event == "pronouncement" and judgment.pronounced_in_presence and not judgment.in_absentia:
            return judgment.date
        if self.start_event == "decision":
            return judgment.date
        return judgment.notified_date or False

    def _ldm_dates(self, company, event_date, calendar=None, cap_from=None):
        """(act by, legal last day) of this period started on ``event_date``."""
        self.ensure_one()
        return company.ldm_statutory_dates(
            event_date, self.days, self.unit, calendar=calendar, extends_on_holiday=self.extends_on_holiday,
            max_months=self.max_months, cap_from=cap_from or event_date)

    def _ldm_deadline_kind(self):
        self.ensure_one()
        return "appeal" if self.remedy in CHALLENGE_REMEDIES else "statutory"

    def _ldm_waits_for_answer(self):
        """True for a period that is someone else's time to answer (an
        authority deciding a grievance): the next period starts when it ends."""
        self.ensure_one()
        return self.next_rule_id.start_event == "previous_deadline_end"

    def _ldm_starts_on_our_step(self):
        """True when this period starts on the day the previous one is met
        (the grievance is lodged, the answer arrives). Periods that count from
        a decision or a notification wait for that date to be entered."""
        self.ensure_one()
        return self.start_event in ("event", "previous_deadline_end", "hearing_outcome")

    def action_view_deadlines(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_deadline")
        action.update({"domain": [("rule_id", "=", self.id)], "context": {"default_rule_id": self.id},
                       "name": _("Deadlines under %s", self.display_name)})
        return action

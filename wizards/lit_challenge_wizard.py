# -*- coding: utf-8 -*-
"""Lodge a challenge against a judgment: the chosen period is met, the other
open challenge periods of the judgment close, and the next court stage opens."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..models.base_litigation import COURT_STAGES
from ..models.lit_rules import ldm_date, ldm_user_is

# The stage a remedy takes the case to. Objection and retrial go back to the
# court that gave the judgment, so they stay at its stage.
STAGE_OF_REMEDY = {
    "appeal": "appeal",
    "cassation": "cassation",
    "cassation_decision": "cassation",
    "correction": "cassation",
}


class LegalJudgmentChallengeWizard(models.TransientModel):
    _name = "legal.judgment.challenge.wizard"
    _description = "Lodge a challenge"

    judgment_id = fields.Many2one("legal.judgment", string="Judgment", required=True, ondelete="cascade")
    task_id = fields.Many2one(related="judgment_id.task_id", string="Matter")
    deadline_id = fields.Many2one(
        "legal.deadline", string="Challenge", compute="_compute_deadline_id", store=True, readonly=False,
        precompute=True,
        domain="[('judgment_id', '=', judgment_id), ('kind', '=', 'appeal'), ('state', 'in', ('open', 'awaiting_service'))]")
    date_lodged = fields.Date(string="Lodged on", required=True, default=fields.Date.context_today)
    stage = fields.Selection(COURT_STAGES, string="Stage", compute="_compute_court", store=True, readonly=False,
                             precompute=True)
    department_id = fields.Many2one("legal.department", string="Court", compute="_compute_court", store=True,
                                    readonly=False, precompute=True, domain="[('body_kind', '=', 'court')]")
    case_number = fields.Char(string="Case number", help="The number the court gives the challenge, if known.")
    case_year = fields.Integer(string="Year", default=lambda self: fields.Date.context_today(self).year)

    @api.depends("judgment_id")
    def _compute_deadline_id(self):
        for wizard in self:
            windows = wizard.judgment_id.deadline_ids.filtered(
                lambda d: d.kind == "appeal" and d.state in ("open", "awaiting_service"))
            wizard.deadline_id = windows.sorted(lambda d: (not d.date_safe, d.date_safe or wizard.date_lodged))[:1]

    @api.depends("deadline_id", "judgment_id")
    def _compute_court(self):
        for wizard in self:
            judgment = wizard.judgment_id
            court = judgment.department_id or judgment.task_id.department_id
            remedy = wizard.deadline_id.rule_id.remedy
            stage = STAGE_OF_REMEDY.get(remedy)
            if stage:
                wizard.stage = stage
                wizard.department_id = court.parent_id or False
            else:
                wizard.stage = judgment.court_stage or judgment.task_id.court_stage or "first_instance"
                wizard.department_id = court

    def action_confirm(self):
        self.ensure_one()
        if not ldm_user_is(self.env, "group_legal_user"):
            raise AccessError(_("Only a lawyer can lodge a challenge."))
        judgment = self.judgment_id
        judgment.check_access("write")
        deadline = self.deadline_id
        if not deadline or deadline.judgment_id != judgment or deadline.state not in ("open", "awaiting_service"):
            raise UserError(_("Choose which challenge was lodged."))
        if deadline.date_deadline and self.date_lodged > deadline.date_deadline:
            raise UserError(_("%(name)s ended on %(date)s: a challenge lodged after that is rejected (Civil "
                              "Procedure Law Art. 171).", name=deadline.name,
                              date=ldm_date(self.env, deadline.date_deadline)))
        deadline.write({"state": "done", "date_done": self.date_lodged})
        others = judgment.deadline_ids.filtered(
            lambda d: d.kind == "appeal" and d.state in ("open", "awaiting_service") and d != deadline)
        if others:
            others.write({"state": "cancelled", "note": _("Another challenge was lodged: %s", deadline.name)})
        line = self.env["legal.court.stage"].create({
            "task_id": judgment.task_id.id,
            "stage": self.stage,
            "department_id": self.department_id.id,
            "case_number": self.case_number,
            "case_year": self.case_year,
            "date_filed": self.date_lodged,
        })
        judgment.task_id.message_post(
            body=_("%(name)s lodged on %(date)s against the judgment of %(judgment)s. New court stage: %(stage)s.",
                   name=deadline.name, date=ldm_date(self.env, self.date_lodged),
                   judgment=ldm_date(self.env, judgment.date), stage=line.display_name),
            message_type="comment", subtype_xmlid="mail.mt_note")
        return {"type": "ir.actions.act_window_close"}

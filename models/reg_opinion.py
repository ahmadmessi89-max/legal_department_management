# -*- coding: utf-8 -*-
"""Legal opinions (الرأي القانوني): issued with a yearly number, frozen, and
revised only by a new opinion that supersedes the old one."""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import is_html_empty

from .ldm_engine import engine_guard, in_engine
from .reg_common import attach_report

OPINION_FROZEN = {"question", "opinion_html", "requesting_unit"}
APPROVER_GROUP = "legal_department_management.group_ldm_approver"
CLOSED_STATES = ("done", "cancelled")


class LegalTask(models.Model):
    _inherit = "legal.task"

    opinion_memo_id = fields.Many2one("ir.attachment", string="Opinion memo", readonly=True, copy=False,
                                      ondelete="set null")
    opinion_issued_by_id = fields.Many2one("res.users", string="Issued by", readonly=True, copy=False)
    ldm_can_issue_opinion = fields.Boolean(compute="_compute_ldm_can_issue_opinion")

    @api.depends_context("uid")
    @api.depends("kind", "opinion_number", "state")
    def _compute_ldm_can_issue_opinion(self):
        approver = self.env.user.has_group(APPROVER_GROUP)
        for task in self:
            task.ldm_can_issue_opinion = bool(approver and task.kind == "opinion" and not task.opinion_number
                                              and task.state not in CLOSED_STATES)

    def write(self, vals):
        if not (in_engine() or self.env.su) and OPINION_FROZEN & set(vals):
            for task in self.filtered("opinion_number"):
                raise UserError(_("Opinion %(number)s was issued on %(date)s and cannot change. "
                                  "Use “Revise opinion” to write a new version that replaces it.",
                                  number=task.opinion_number, date=task.opinion_date))
        return super().write(vals)

    def action_issue_opinion(self):
        """Give the opinion its yearly number and date, freeze it and attach the
        opinion memo (مذكرة رأي قانوني)."""
        if not self.env.user.has_group(APPROVER_GROUP):
            raise AccessError(_("Only an approver or a legal manager can issue an opinion."))
        self.check_access("write")
        today = fields.Date.context_today(self)
        sequence = self.env["ir.sequence"].sudo().search([("code", "=", "legal.opinion"),
                                                           ("company_id", "in", [self.env.company.id, False])],
                                                          order="company_id", limit=1)
        for task in self:
            if task.kind != "opinion":
                raise UserError(_("%s is not a legal opinion.", task.display_name))
            if task.opinion_number:
                raise UserError(_("%(matter)s was already issued as opinion %(number)s.",
                                  matter=task.display_name, number=task.opinion_number))
            if task.state in CLOSED_STATES:
                raise UserError(_("%s is closed.", task.display_name))
            if not (task.question or "").strip() or is_html_empty(task.opinion_html):
                raise UserError(_("Write the question and the opinion before issuing it."))
            number = sequence._next(sequence_date=today) if sequence else str(task.id)
            with engine_guard():
                task.write({"opinion_number": number, "opinion_date": today,
                            "opinion_issued_by_id": self.env.uid})
            memo = attach_report(self.env, "legal_department_management.action_report_ldm_opinion_memo", task,
                                 _("Legal opinion %s", number))
            task.write({"opinion_memo_id": memo.id, "attachment_ids": [(4, memo.id)]})
            task.message_post(body=_("Opinion %(number)s issued by %(user)s.", number=number,
                                     user=self.env.user.name), attachment_ids=memo.ids)
            if task.supersedes_id:
                task.supersedes_id.message_post(body=_("Replaced by opinion %s.", number))
        return True

    def action_ldm_revise_opinion(self):
        """A revision is a new opinion that supersedes this one; the issued text
        is never reopened."""
        self.ensure_one()
        if not self.opinion_number:
            raise UserError(_("Only an issued opinion can be revised. Until it is issued, edit it."))
        if self.superseded_by_id:
            raise UserError(_("%(matter)s is already revised by %(revision)s.", matter=self.display_name,
                              revision=self.superseded_by_id.display_name))
        self.check_access("write")
        # Copied with sudo: a plain copy also reads the legacy accounting
        # fields, which a lawyer without accounting rights may not read.
        revision = self.sudo().copy({
            "name": _("%s (revision)", self.name),
            "supersedes_id": self.id,
            "question": self.question,
            "opinion_html": self.opinion_html,
            "requesting_unit": self.requesting_unit,
        })
        revision = revision.with_env(self.env)
        with engine_guard():
            self.write({"superseded_by_id": revision.id})
        self.message_post(body=_("Revision started: %s.", revision.display_name))
        return {
            "type": "ir.actions.act_window",
            "res_model": "legal.task",
            "res_id": revision.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_ldm_download_memo(self):
        self.ensure_one()
        if not self.opinion_memo_id:
            raise UserError(_("This opinion has no memo yet: it is attached when the opinion is issued."))
        return {"type": "ir.actions.act_url", "url": f"/web/content/{self.opinion_memo_id.id}?download=true",
                "target": "self"}

# -*- coding: utf-8 -*-
"""Judgments and their challenge deadlines. Recording a judgment, or writing
the date it was served, proposes every applicable statutory period; changing a
date recounts the open ones and says on the matter what moved."""
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import format_date

from .lit_rules import LAW_OF_BRANCH
from .lit_rules import ldm_user_is

OPEN = ("open", "awaiting_service")
# Writing any of these recounts the judgment's deadlines.
TRIGGERS = {"date", "notified_date", "pronounced_in_presence", "law", "court_degree", "in_absentia", "result",
            "department_id"}


class LegalJudgment(models.Model):
    _inherit = "legal.judgment"

    open_deadline_count = fields.Integer(string="Open deadlines", compute="_compute_deadline_info")
    ldm_can_challenge = fields.Boolean(compute="_compute_deadline_info")
    next_deadline_label = fields.Char(string="Next deadline", compute="_compute_deadline_info")

    @api.depends("deadline_ids.state", "deadline_ids.date_safe", "deadline_ids.kind")
    @api.depends_context("lang")
    def _compute_deadline_info(self):
        Deadline = self.env["legal.deadline"]
        for judgment in self:
            opened = judgment.deadline_ids.filtered(lambda d: d.state in OPEN)
            judgment.open_deadline_count = len(opened)
            judgment.ldm_can_challenge = bool(opened.filtered(lambda d: d.kind == "appeal"))
            first = opened.sorted(lambda d: (not d.date_safe, d.date_safe or fields.Date.today()))[:1]
            judgment.next_deadline_label = Deadline._ldm_describe(first) if first else False

    @api.depends("date", "result", "task_id.task_number")
    def _compute_display_name(self):
        results = dict(self._fields["result"]._description_selection(self.env))
        for judgment in self:
            parts = [_("Judgment"), format_date(self.env, judgment.date) if judgment.date else "",
                     results.get(judgment.result, "")]
            judgment.display_name = " · ".join(p for p in parts if p)

    @api.constrains("date", "notified_date")
    def _check_notified_date(self):
        for judgment in self:
            if judgment.date and judgment.notified_date and judgment.notified_date < judgment.date:
                raise ValidationError(_("A judgment cannot be served before it is given."))

    # ------------------------------------------------------------------
    # Defaults from the matter
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        task = self.env["legal.task"].browse(values.get("task_id") or self.env.context.get("default_task_id") or [])
        if task.exists():
            values.update({k: v for k, v in self._ldm_values_from_task(task).items()
                           if k in fields_list and not self.env.context.get(f"default_{k}")})
        return values

    @api.model
    def _ldm_values_from_task(self, task):
        values = {"law": LAW_OF_BRANCH.get(task.law_branch or "civil", "civil")}
        if task.department_id.body_kind == "court":
            values["department_id"] = task.department_id.id
            if task.department_id.court_degree:
                values["court_degree"] = task.department_id.court_degree
        if task.court_stage:
            values["court_stage"] = task.court_stage
        return values

    @api.onchange("department_id")
    def _onchange_department_degree(self):
        if self.department_id.court_degree:
            self.court_degree = self.department_id.court_degree

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        Task = self.env["legal.task"]
        for vals in vals_list:
            if vals.get("task_id"):
                for key, value in self._ldm_values_from_task(Task.browse(vals["task_id"])).items():
                    vals.setdefault(key, value)
        judgments = super().create(vals_list)
        judgments._ldm_generate_deadlines(post=False)
        for judgment in judgments:
            line = judgment.task_id.court_stage_ids.sorted(lambda l: (l.sequence, l.id))[-1:]
            if line and not line.judgment_id:
                line.judgment_id = judgment
        return judgments

    def write(self, vals):
        result = super().write(vals)
        if TRIGGERS & set(vals):
            self._ldm_generate_deadlines(post=True)
        return result

    def unlink(self):
        if not ldm_user_is(self.env, "group_legal_manager"):
            raise AccessError(_("Only a legal manager can delete a judgment."))
        return super().unlink()

    # ------------------------------------------------------------------
    # The engine
    # ------------------------------------------------------------------
    def _ldm_calendar(self):
        self.ensure_one()
        court = self.department_id or self.task_id.department_id
        if court:
            return court._ldm_calendar()
        return (self.company_id or self.env.company)._ldm_calendar()

    def _ldm_generate_deadlines(self, post=True):
        """Create the deadline of every applicable statutory period once, recount
        the open ones, and cancel the open ones that no longer apply. Idempotent
        per (judgment, period)."""
        Deadline = self.env["legal.deadline"]
        rules = self.env["legal.appeal.rule"].search([("from_judgment", "=", True)])
        for judgment in self:
            if not judgment.task_id:
                continue
            applicable = rules.filtered(lambda r: r._ldm_matches(judgment))
            ours = judgment.result != "for"
            existing = judgment.deadline_ids.filtered(lambda d: d.source_model == self._name and d.rule_id)
            created = Deadline
            moves = []
            for rule in applicable:
                deadline = existing.filtered(lambda d, r=rule: d.rule_id == r)[:1]
                if not deadline:
                    created |= Deadline.create({
                        "task_id": judgment.task_id.id,
                        "judgment_id": judgment.id,
                        "rule_id": rule.id,
                        "name": rule.name if ours else _("%s (other side)", rule.name),
                        "kind": rule._ldm_deadline_kind(),
                        "our_action": ours,
                        "state": "awaiting_service",
                        "source_model": self._name,
                        "source_id": judgment.id,
                    })
                    continue
                if deadline.state not in OPEN:
                    continue
                if deadline.our_action != ours:
                    deadline.write({"our_action": ours,
                                    "name": rule.name if ours else _("%s (other side)", rule.name)})
                moves += deadline._ldm_recompute_dates()
            stale = existing.filtered(lambda d: d.state in OPEN and d.rule_id not in applicable)
            if stale:
                stale.write({"state": "cancelled", "note": _("No longer applies to this judgment.")})
            if post and (moves or stale or created):
                judgment._ldm_post_changes(created, moves, stale)
        return True

    def _ldm_post_changes(self, created, moves, stale):
        self.ensure_one()
        Deadline = self.env["legal.deadline"]
        lines = [Deadline._ldm_describe(d) for d in created]
        for deadline, old_safe, new_safe, _old_legal, new_legal in moves:
            now = Deadline._ldm_describe(deadline, new_safe, new_legal)
            lines.append(_("%(now)s (was %(old)s)", now=now, old=format_date(self.env, old_safe)) if old_safe else now)
        for deadline in stale:
            lines.append(_("%s: no longer applies", deadline.name))
        users = self.task_id.lawyer_id
        for move in moves:
            users |= move[0].user_id
        partners = users.filtered("active").partner_id
        body = Markup("<p>%s</p><ul>%s</ul>") % (
            _("Deadlines of the judgment of %s recounted:", format_date(self.env, self.date)),
            Markup("").join(Markup("<li>%s</li>") % line for line in lines))
        self.task_id.message_post(body=body, partner_ids=partners.ids, message_type="comment",
                                  subtype_xmlid="mail.mt_note")

    def _ldm_update_final_date(self):
        """A judgment is final once every challenge period has ended with no
        challenge lodged (اكتسب الدرجة القطعية)."""
        for judgment in self:
            if judgment.final_date:
                continue
            windows = judgment.deadline_ids.filtered(lambda d: d.kind == "appeal" and d.state != "cancelled")
            if not windows or windows.filtered(lambda d: d.state in OPEN + ("done",)):
                continue
            last = max(d.date_deadline or d.date_safe for d in windows)
            judgment.final_date = last + timedelta(days=1)
            judgment.task_id.message_post(
                body=_("The judgment of %(date)s became final on %(final)s: no challenge was lodged in time.",
                       date=format_date(self.env, judgment.date), final=format_date(self.env, judgment.final_date)),
                message_type="comment", subtype_xmlid="mail.mt_note")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def ldm_set_notified_date(self, notified_date):
        """Interface (SPEC 14.1), used by My Day: record the service date. The
        challenge deadlines are counted from it by write()."""
        if not ldm_user_is(self.env, "group_legal_user"):
            raise AccessError(_("Only a lawyer can record when a judgment was served."))
        self.write({"notified_date": notified_date})
        return True

    def action_ldm_lodge_challenge(self):
        self.ensure_one()
        if not ldm_user_is(self.env, "group_legal_user"):
            raise AccessError(_("Only a lawyer can lodge a challenge."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Lodge a challenge"),
            "res_model": "legal.judgment.challenge.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_judgment_id": self.id},
        }

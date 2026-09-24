# -*- coding: utf-8 -*-
"""Court stages: each line is one court and its case number. The matter's
court_stage and court_case_number mirror the latest line; an execution line
with the date the execution notice was served starts the debtor's period."""
from odoo import _, api, models

EXECUTION_NOTICE_RULE = "legal_department_management.ldm_rule_exe_1"


class LegalCourtStage(models.Model):
    _inherit = "legal.court.stage"

    @api.depends("stage", "case_number", "case_year", "department_id")
    def _compute_display_name(self):
        stages = dict(self._fields["stage"]._description_selection(self.env))
        for line in self:
            parts = [stages.get(line.stage, ""), line._ldm_case_number() or "", line.department_id.name or ""]
            line.display_name = " · ".join(p for p in parts if p)

    def _ldm_case_number(self):
        """The case number as courts write it: number/year."""
        self.ensure_one()
        number = (self.case_number or "").strip()
        if not number:
            return False
        if self.case_year and str(self.case_year) not in number:
            return f"{number}/{self.case_year}"
        return number

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("task_id") and "sequence" not in vals:
                lines = self.search([("task_id", "=", vals["task_id"])])
                vals["sequence"] = max(lines.mapped("sequence") or [0]) + 1
        lines = super().create(vals_list)
        lines.task_id._ldm_sync_court_stage()
        lines._ldm_execution_notice()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if {"stage", "case_number", "case_year", "sequence"} & set(vals):
            self.task_id._ldm_sync_court_stage()
        if {"stage", "notification_date"} & set(vals):
            self._ldm_execution_notice()
        return result

    def unlink(self):
        tasks = self.task_id
        result = super().unlink()
        tasks.exists()._ldm_sync_court_stage()
        return result

    def _ldm_execution_notice(self):
        """The debtor has 7 days after the execution notice (Execution Law 45
        of 1980, Art. 18): keep one deadline per execution line."""
        rule = self.env.ref(EXECUTION_NOTICE_RULE, raise_if_not_found=False)
        if not rule:
            return
        Deadline = self.env["legal.deadline"]
        for line in self.filtered(lambda l: l.stage == "execution" and l.notification_date):
            deadline = Deadline.search([("source_model", "=", self._name), ("source_id", "=", line.id),
                                        ("rule_id", "=", rule.id)], limit=1)
            if deadline:
                if deadline.state in ("open", "awaiting_service") and deadline.date_start != line.notification_date:
                    deadline.write({"date_start": line.notification_date})
                continue
            # The period is the debtor's: when we act for the creditor it only
            # tells us when enforcement may go ahead.
            ours = line.task_id.our_role not in ("plaintiff", "complainant")
            Deadline.create({
                "task_id": line.task_id.id,
                "rule_id": rule.id,
                "name": rule.name if ours else _("%s (other side)", rule.name),
                "date_start": line.notification_date,
                "source_model": self._name,
                "source_id": line.id,
                "our_action": ours,
            })

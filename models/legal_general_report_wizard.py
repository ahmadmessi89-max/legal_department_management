# -*- coding: utf-8 -*-
import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .legal_company_report_wizard import STATE_FILTER


class LegalGeneralReportWizard(models.TransientModel):
    """Options for the oversight report. Opened from the Matters list it takes
    the selected matters (or the whole filtered list); opened from Reporting it
    starts with every open matter."""

    _name = "legal.general.report.wizard"
    _description = "Oversight report options"

    company_ids = fields.Many2many("legal.company", "legal_general_report_company_rel", "wizard_id", "company_id",
                                   string="Clients", help="Leave empty for every client.")
    filter_lawyer_id = fields.Many2one("res.users", string="Responsible", domain="[('share', '=', False)]")
    filter_department_id = fields.Many2one("legal.department", string="Body or court")
    filter_state = fields.Selection(STATE_FILTER, string="Matters", required=True, default="open")
    date_from = fields.Date(string="Dates from", help="Matters whose target date or next date falls in the period.")
    date_to = fields.Date(string="Dates to")
    group_by_company = fields.Boolean(string="Group by client", default=True)
    filter_task_ids = fields.Many2many("legal.task", "legal_gen_report_wizard_task_rel", "wizard_id", "task_id",
                                       string="Selected matters")
    task_domain = fields.Char(string="Filter of the list", readonly=True)
    selection_note = fields.Char(compute="_compute_selection_note")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        context = self.env.context
        model = context.get("active_model")
        if model == "legal.task":
            if context.get("active_domain") is not None and not context.get("active_ids"):
                values["task_domain"] = repr(context["active_domain"])
                values["filter_state"] = "all"
            elif context.get("active_ids"):
                values["filter_task_ids"] = [(6, 0, context["active_ids"])]
                values["filter_state"] = "all"
        elif model == "legal.company" and context.get("active_ids"):
            values["company_ids"] = [(6, 0, context["active_ids"])]
        return values

    @api.depends("filter_task_ids", "task_domain")
    def _compute_selection_note(self):
        for wizard in self:
            if wizard.filter_task_ids:
                wizard.selection_note = _("%s matters selected in the list.", len(wizard.filter_task_ids))
            elif wizard.task_domain:
                wizard.selection_note = _("The matters of the filtered list.")
            else:
                wizard.selection_note = False

    def _ldm_report_data(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise UserError(_("The end date is before the start date."))
        data = {
            "filtered": True,
            "client_ids": self.company_ids.ids,
            "lawyer_id": self.filter_lawyer_id.id or False,
            "department_id": self.filter_department_id.id or False,
            "state": self.filter_state,
            "date_from": fields.Date.to_string(self.date_from) if self.date_from else False,
            "date_to": fields.Date.to_string(self.date_to) if self.date_to else False,
            "group_by_client": self.group_by_company,
        }
        if self.filter_task_ids:
            data["task_ids"] = self.filter_task_ids.ids
        if self.task_domain:
            data["domain"] = ast.literal_eval(self.task_domain)
        return data

    def action_print_general_report(self):
        self.ensure_one()
        return self.env.ref("legal_department_management.action_report_legal_general_overview").report_action(
            self.env["legal.task"], data=self._ldm_report_data(), config=False)

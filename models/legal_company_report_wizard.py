# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

STATE_FILTER = [("all", "All matters"), ("open", "Open matters"), ("closed", "Done or cancelled")]


class LegalCompanyReportWizard(models.TransientModel):
    """Options for the client file. The options travel as report data, so the
    printed file is exactly what was chosen here; a choice that matches no
    matter prints an empty list, never the whole file."""

    _name = "legal.company.report.wizard"
    _description = "Client file options"

    company_id = fields.Many2one("legal.company", string="Client", required=True, ondelete="cascade")
    show_company_info = fields.Boolean(string="Print the registration details", default=True)
    filter_state = fields.Selection(STATE_FILTER, string="Matters", required=True, default="all")
    filter_lawyer_id = fields.Many2one("res.users", string="Responsible", domain="[('share', '=', False)]")
    filter_department_id = fields.Many2one("legal.department", string="Body or court")
    filter_task_ids = fields.Many2many("legal.task", "legal_report_wizard_task_rel", "wizard_id", "task_id",
                                       string="Only these matters", domain="[('legal_company_id', '=', company_id)]")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        context = self.env.context
        if "company_id" in fields_list and not values.get("company_id") and \
                context.get("active_model") == "legal.company" and context.get("active_id"):
            values["company_id"] = context["active_id"]
        return values

    def _ldm_report_data(self):
        self.ensure_one()
        data = {
            "filtered": True,
            "client_ids": [self.company_id.id],
            "show_company_info": self.show_company_info,
            "state": self.filter_state,
            "lawyer_id": self.filter_lawyer_id.id or False,
            "department_id": self.filter_department_id.id or False,
        }
        if self.filter_task_ids:
            data["task_ids"] = self.filter_task_ids.ids
        return data

    def action_print_report(self):
        self.ensure_one()
        if not self.company_id:
            raise UserError(_("Choose the client."))
        return self.env.ref("legal_department_management.action_report_legal_company").report_action(
            self.company_id, data=self._ldm_report_data(), config=False)

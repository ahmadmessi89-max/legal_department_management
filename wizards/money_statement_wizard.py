# -*- coding: utf-8 -*-
"""The client statement of account (كشف حساب): the dialog that asks for the
period, and the report model that computes it."""
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


def _can_read_accounts(env):
    return env.su or env.user.has_group("account.group_account_invoice") \
        or env.user.has_group("account.group_account_readonly")


class LegalStatementWizard(models.TransientModel):
    _name = "legal.statement.wizard"
    _description = "Statement of account"

    legal_company_id = fields.Many2one("legal.company", string="Client", required=True)
    date_from = fields.Date(string="From", required=True,
                            default=lambda self: date(fields.Date.context_today(self).year, 1, 1))
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)

    def action_print(self):
        self.ensure_one()
        if not _can_read_accounts(self.env):
            raise AccessError(_("The statement of account is prepared by billing."))
        if self.date_from > self.date_to:
            raise UserError(_("The period ends before it starts."))
        data = {"date_from": fields.Date.to_string(self.date_from), "date_to": fields.Date.to_string(self.date_to)}
        return self.env.ref("legal_department_management.action_report_ldm_statement").report_action(
            self.legal_company_id, data=data)

    def action_message(self):
        """Tell the client the statement is ready (WhatsApp or email)."""
        self.ensure_one()
        return self.env["legal.client.message.wizard"].ldm_open("statement_ready", client=self.legal_company_id)


class ReportLdmStatement(models.AbstractModel):
    _name = "report.legal_department_management.report_ldm_statement"
    _description = "Statement of account report"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not _can_read_accounts(self.env):
            raise AccessError(_("The statement of account is prepared by billing."))
        data = data or {}
        today = fields.Date.context_today(self)
        date_from = fields.Date.to_date(data.get("date_from")) or date(today.year, 1, 1)
        date_to = fields.Date.to_date(data.get("date_to")) or today
        docs = self.env["legal.company"].browse(docids)
        docs.check_access("read")
        return {
            "doc_ids": docids,
            "doc_model": "legal.company",
            "docs": docs,
            "date_from": date_from,
            "date_to": date_to,
            "sections": {doc.id: doc._ldm_statement(date_from, date_to) for doc in docs},
        }

# -*- coding: utf-8 -*-
"""Readiness at a date (SPEC 14.6, research 03 C10).

A tender closes on the 15th: will the client's tax clearance, chamber ID and
social-security clearance still be valid that day? The dialog takes a client,
a date and a matter type used as a document pack, and lists each document the
type asks for with whether the client's records hold a copy valid on that date.
"""
from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.tools.misc import format_date

READINESS = [
    ("valid", "Valid on that date"),
    ("expires", "Expires before that date"),
    ("missing", "Not in the records"),
]


class LegalReadinessWizard(models.TransientModel):
    _name = "legal.readiness.wizard"
    _description = "Documents valid at a date"

    legal_company_id = fields.Many2one("legal.company", string="Client", required=True)
    date = fields.Date(string="Needed on", required=True, default=fields.Date.context_today)
    template_id = fields.Many2one("legal.task.template", string="Document pack",
                                  domain="[('document_ids', '!=', False)]",
                                  help="A matter type whose documents to collect make up the pack, e.g. a tender file.")
    line_ids = fields.One2many("legal.readiness.wizard.line", "wizard_id", string="Documents",
                               compute="_compute_line_ids", store=True, readonly=True)
    ready_count = fields.Integer(compute="_compute_summary")
    total_count = fields.Integer(compute="_compute_summary")
    summary = fields.Char(compute="_compute_summary")

    @api.model
    def _ldm_open(self, context):
        return {
            "type": "ir.actions.act_window",
            "name": _("Documents valid at a date"),
            "res_model": "legal.readiness.wizard",
            "view_mode": "form",
            "views": [(self.env.ref("legal_department_management.view_legal_readiness_wizard_form").id, "form")],
            "target": "new",
            "context": context,
        }

    @api.depends("legal_company_id", "date", "template_id")
    def _compute_line_ids(self):
        for wizard in self:
            rows = wizard._ldm_check() if wizard.legal_company_id and wizard.date else []
            wizard.line_ids = [Command.clear()] + [Command.create(values) for values in rows]

    @api.depends("line_ids.readiness", "legal_company_id", "date")
    def _compute_summary(self):
        for wizard in self:
            lines = wizard.line_ids
            wizard.total_count = len(lines)
            wizard.ready_count = len(lines.filtered(lambda line: line.readiness == "valid"))
            if not wizard.legal_company_id or not wizard.date:
                wizard.summary = False
            elif not lines:
                wizard.summary = _("Choose a document pack, or file documents in the client's records.")
            else:
                wizard.summary = _("%(ready)s of %(total)s documents valid on %(date)s",
                                   ready=wizard.ready_count, total=wizard.total_count,
                                   date=format_date(self.env, wizard.date))

    def _ldm_check(self):
        """One row per document type of the pack (or, without a pack, per type
        the client holds): the best copy on file and whether it is valid then."""
        self.ensure_one()
        Vault = self.env["legal.company.document"]
        vault = Vault.search([("legal_company_id", "=", self.legal_company_id.id)])
        if self.template_id:
            wanted = [(line.document_type_id, line.mandatory) for line in self.template_id.document_ids]
        else:
            wanted = [(doc_type, True) for doc_type in vault.document_type_id]
        rows = []
        for sequence, (doc_type, mandatory) in enumerate(wanted, start=1):
            copies = vault.filtered(lambda d, t=doc_type: d.document_type_id == t and d.active)
            valid = copies._ldm_valid_on(self.date)[:1]
            if valid:
                best, readiness = valid, "valid"
            elif copies:
                best = copies.sorted(lambda d: d.date_expiry or fields.Date.to_date("1900-01-01"), reverse=True)[:1]
                readiness = "expires"
            else:
                best, readiness = Vault, "missing"
            rows.append({
                "sequence": sequence,
                "document_type_id": doc_type.id,
                "mandatory": mandatory,
                "company_document_id": best.id or False,
                "date_expiry": best.date_expiry or False,
                "readiness": readiness,
            })
        return rows


class LegalReadinessWizardLine(models.TransientModel):
    _name = "legal.readiness.wizard.line"
    _description = "Document valid at a date"
    _order = "sequence, id"

    wizard_id = fields.Many2one("legal.readiness.wizard", ondelete="cascade")
    sequence = fields.Integer()
    document_type_id = fields.Many2one("legal.document.type", string="Document", readonly=True)
    mandatory = fields.Boolean(string="Mandatory", readonly=True)
    company_document_id = fields.Many2one("legal.company.document", string="Copy on file", readonly=True)
    date_expiry = fields.Date(string="Expires on", readonly=True)
    readiness = fields.Selection(READINESS, string="On that date", readonly=True)

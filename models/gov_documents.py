# -*- coding: utf-8 -*-
"""The documents to collect for a matter (legal.task.document).

A document moves missing -> received -> (awaiting confirmation ->) verified,
or ends expired or not needed. "Verified" is صحة صدور: the issuing body has
confirmed the paper is genuine. Asking for that confirmation hands the matter
to the issuing body, so the matter's ``waiting_on`` follows the documents.
A valid document already filed in the client's records is taken from there
instead of being collected again.
"""
import base64
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

HELD_STATES = ("received", "awaiting_verification", "verified")


class LegalDocumentType(models.Model):
    _inherit = "legal.document.type"

    def _ldm_expiry_from(self, start):
        """Expiry implied by this type for a copy issued (or received) on ``start``."""
        self.ensure_one()
        if start and self.validity in ("fixed_days", "freshness_days") and self.validity_days:
            return start + timedelta(days=self.validity_days)
        return False


class LegalTaskDocument(models.Model):
    _inherit = "legal.task.document"

    state = fields.Selection(
        selection_add=[("received",), ("awaiting_verification", "Awaiting confirmation"), ("verified",)],
        ondelete={"awaiting_verification": "set default"})
    legal_company_id = fields.Many2one(related="task_id.legal_company_id", string="Client")
    verification_ref = fields.Char(string="Confirmation reference",
                                   help="Number of the body's confirmation letter, or the QR reference of a notary document.")
    verification_date = fields.Date(string="Confirmed on")
    file_data = fields.Binary(string="Scan", compute="_compute_file_data", inverse="_inverse_file_data")
    file_name = fields.Char(string="File name", compute="_compute_file_data", inverse="_inverse_file_data")
    ldm_vault_on = fields.Boolean(compute="_compute_ldm_vault_on")
    ldm_in_vault = fields.Boolean(string="In the client's records", compute="_compute_ldm_in_vault",
                                  help="The client's records hold a copy of this document that is valid today.")

    @api.depends("attachment_id")
    def _compute_file_data(self):
        for doc in self:
            doc.file_data = doc.attachment_id.datas if doc.attachment_id else False
            doc.file_name = doc.attachment_id.name if doc.attachment_id else False

    def _inverse_file_data(self):
        """Uploading the scan of a missing document means we now have it."""
        for doc in self:
            if not doc.file_data:
                continue
            if doc.attachment_id and doc.attachment_id.datas == doc.file_data:
                continue
            attachment = self.env["ir.attachment"].create({
                "name": doc.file_name or doc.name,
                "datas": doc.file_data,
                "res_model": "legal.task",
                "res_id": doc.task_id.id,
            })
            values = {"attachment_id": attachment.id}
            if doc.state in ("missing", "expired"):
                values["state"] = "received"
            doc.write(values)

    def _compute_ldm_vault_on(self):
        on = self.env["legal.task"]._ldm_feature("group_ldm_corporate")
        for doc in self:
            doc.ldm_vault_on = on

    @api.depends("document_type_id", "task_id.legal_company_id")
    def _compute_ldm_in_vault(self):
        """One search for the whole list: which (client, type) pairs the vault
        holds a copy of that is valid today."""
        today = fields.Date.context_today(self)
        wanted = self.filtered(lambda d: d.document_type_id and d.task_id.legal_company_id)
        held = set()
        if wanted and self.env["legal.task"]._ldm_feature("group_ldm_corporate"):
            vault = self.env["legal.company.document"].search([
                ("legal_company_id", "in", wanted.task_id.legal_company_id.ids),
                ("document_type_id", "in", wanted.document_type_id.ids),
            ])
            held = {(d.legal_company_id.id, d.document_type_id.id) for d in vault._ldm_valid_on(today)}
        for doc in self:
            doc.ldm_in_vault = (doc.task_id.legal_company_id.id, doc.document_type_id.id) in held

    # ------------------------------------------------------------------
    # State flow
    # ------------------------------------------------------------------
    @api.onchange("state")
    def _onchange_state_dates(self):
        today = fields.Date.context_today(self)
        if self.state in HELD_STATES and not self.received_date:
            self.received_date = today
        if self.state == "verified" and not self.verification_date:
            self.verification_date = today
        if self.state in HELD_STATES and not self.expiry_date and self.document_type_id:
            self.expiry_date = self.document_type_id._ldm_expiry_from(self.received_date)

    @api.model_create_multi
    def create(self, vals_list):
        documents = super().create(vals_list)
        documents._ldm_fill_dates()
        documents.task_id._ldm_sync_verification()
        return documents

    def write(self, vals):
        result = super().write(vals)
        if "state" in vals:
            self._ldm_fill_dates()
            self.task_id._ldm_sync_verification()
        return result

    def _ldm_fill_dates(self):
        today = fields.Date.context_today(self)
        for doc in self:
            values = {}
            if doc.state in HELD_STATES and not doc.received_date:
                values["received_date"] = today
            if doc.state == "verified" and not doc.verification_date:
                values["verification_date"] = today
            if doc.state in HELD_STATES and not doc.expiry_date and doc.document_type_id:
                expiry = doc.document_type_id._ldm_expiry_from(values.get("received_date") or doc.received_date)
                if expiry:
                    values["expiry_date"] = expiry
            if values:
                super(LegalTaskDocument, doc).write(values)

    def action_ldm_mark_received(self):
        self.write({"state": "received"})
        return True

    def action_ldm_request_verification(self):
        """Ask the issuing body to confirm the document (صحة صدور)."""
        for doc in self:
            if doc.state not in ("received", "verified"):
                raise UserError(_("Receive “%s” before asking the issuing body to confirm it.", doc.name))
        self.write({"state": "awaiting_verification"})
        return True

    def action_ldm_mark_verified(self):
        self.write({"state": "verified"})
        return True

    # ------------------------------------------------------------------
    # The client's records (document vault)
    # ------------------------------------------------------------------
    def _ldm_vault_candidates(self, on_date=None):
        """Documents of the same type in the client's records that are valid on ``on_date``."""
        self.ensure_one()
        if not self.document_type_id or not self.task_id.legal_company_id:
            return self.env["legal.company.document"]
        return self.env["legal.company.document"].search([
            ("legal_company_id", "=", self.task_id.legal_company_id.id),
            ("document_type_id", "=", self.document_type_id.id),
        ])._ldm_valid_on(on_date or fields.Date.context_today(self))

    def action_ldm_take_from_vault(self):
        """Use the valid copy the client's records already hold."""
        if not self.env["legal.task"]._ldm_feature("group_ldm_corporate"):
            raise UserError(_("Company records are switched off in Settings."))
        today = fields.Date.context_today(self)
        for doc in self:
            held = doc._ldm_vault_candidates(today)[:1]
            if not held:
                raise UserError(_("%(client)s has no valid “%(type)s” in its records. Collect it and add it to the matter.",
                                  client=doc.task_id.legal_company_id.name, type=doc.document_type_id.name or doc.name))
            values = {
                "company_document_id": held.id,
                "expiry_date": held.date_expiry or False,
                "received_date": today,
                "state": "received",
            }
            if held.attachment_id:
                values["attachment_id"] = held.attachment_id.copy(
                    {"res_model": "legal.task", "res_id": doc.task_id.id}).id
            doc.write(values)
        return True

    def action_ldm_save_to_vault(self):
        """File a received document in the client's records so the next matter can reuse it."""
        if not self.env["legal.task"]._ldm_feature("group_ldm_corporate"):
            raise UserError(_("Company records are switched off in Settings."))
        if not self.env.user.has_group("legal_department_management.group_legal_user"):
            raise UserError(_("Only a lawyer can add documents to a client's records."))
        Vault = self.env["legal.company.document"]
        for doc in self:
            if doc.company_document_id:
                continue
            if doc.state not in HELD_STATES or not doc.document_type_id:
                raise UserError(_("Only a received document with a document type can be filed in the client's records."))
            values = {
                "legal_company_id": doc.task_id.legal_company_id.id,
                "document_type_id": doc.document_type_id.id,
                "name": doc.name,
                "date_issued": doc.received_date,
                "date_expiry": doc.expiry_date,
            }
            if doc.attachment_id:
                values["attachment_id"] = doc.attachment_id.copy({"res_model": "legal.company.document", "res_id": 0}).id
            vault_doc = Vault.create(values)
            if vault_doc.attachment_id:
                vault_doc.attachment_id.res_id = vault_doc.id
            doc.company_document_id = vault_doc
        return True

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------
    @api.model
    def _cron_ldm_mark_expired(self):
        """Daily: a held document past its expiry date becomes expired, and the
        matter says so once."""
        today = fields.Date.context_today(self)
        expired = self.sudo().search([("state", "in", HELD_STATES), ("expiry_date", "!=", False),
                                      ("expiry_date", "<", today)])
        if not expired:
            return True
        expired.write({"state": "expired"})
        for task, docs in expired.grouped("task_id").items():
            lines = Markup("<br/>").join(
                escape(_("%(name)s expired on %(date)s.", name=d.name, date=format_date(self.env, d.expiry_date)))
                for d in docs)
            task.message_post(body=lines, subtype_xmlid="mail.mt_note")
        return True


class LegalTask(models.Model):
    _inherit = "legal.task"

    def _ldm_set_waiting_on(self, value, on_date=None):
        """Hand the matter to someone. The clock at the body restarts whenever
        the file goes back out to the body (or to the issuing body for confirmation)."""
        outside = ("body", "verification")
        on_date = on_date or fields.Date.context_today(self)
        for task in self:
            values = {}
            if task.waiting_on != value:
                values["waiting_on"] = value
            if value in outside and (task.waiting_on not in outside or not task.date_submitted):
                values["date_submitted"] = on_date
            if values:
                task.write(values)

    def _ldm_sync_verification(self):
        for task in self:
            awaiting = task.document_ids.filtered(lambda d: d.state == "awaiting_verification")
            if awaiting and task.waiting_on != "verification":
                task._ldm_set_waiting_on("verification")
            elif not awaiting and task.waiting_on == "verification":
                task._ldm_set_waiting_on("us")

    def action_ldm_upload_to_document(self, document_id, name, data):
        """Attach a file to one required document from the matter screen (used by
        the documents checklist); ``data`` is base64."""
        self.ensure_one()
        doc = self.document_ids.filtered(lambda d: d.id == document_id)
        if not doc:
            raise UserError(_("This document is not part of %s.", self.display_name))
        base64.b64decode(data, validate=True)
        doc.write({"file_name": name, "file_data": data})
        return True

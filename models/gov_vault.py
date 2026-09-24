# -*- coding: utf-8 -*-
"""The client's document vault (legal.company.document).

A company's registration certificate, tax clearance, chamber ID and powers of
attorney expire, and expiry is what a legal department is chased for most. Each
document that is about to expire keeps exactly one open deadline (kind
"expiry", on the client, with no matter), so it shows on the deadline board and
the agenda next to court deadlines. Renewing the document closes it.
"""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.tools.misc import format_date

VAULT = "legal.company.document"


class LegalCompanyDocument(models.Model):
    _inherit = "legal.company.document"

    file_data = fields.Binary(string="Scan", compute="_compute_file_data", inverse="_inverse_file_data")
    file_name = fields.Char(string="File name", compute="_compute_file_data", inverse="_inverse_file_data")
    validity = fields.Selection(related="document_type_id.validity")
    category = fields.Selection(related="document_type_id.category", store=True, string="Category")
    deadline_id = fields.Many2one("legal.deadline", string="Expiry deadline", compute="_compute_deadline_id")

    @api.depends("attachment_id")
    def _compute_file_data(self):
        for doc in self:
            doc.file_data = doc.attachment_id.datas if doc.attachment_id else False
            doc.file_name = doc.attachment_id.name if doc.attachment_id else False

    def _inverse_file_data(self):
        for doc in self:
            if not doc.file_data or (doc.attachment_id and doc.attachment_id.datas == doc.file_data):
                continue
            doc.attachment_id = self.env["ir.attachment"].create({
                "name": doc.file_name or doc.document_type_id.name or _("Document"),
                "datas": doc.file_data,
                "res_model": VAULT,
                "res_id": doc.id,
            })

    def _compute_deadline_id(self):
        deadlines = self.env["legal.deadline"].search([("source_model", "=", VAULT), ("source_id", "in", self.ids),
                                                        ("state", "=", "open")])
        by_doc = {d.source_id: d for d in deadlines}
        for doc in self:
            doc.deadline_id = by_doc.get(doc.id, False)

    @api.onchange("date_issued", "document_type_id")
    def _onchange_date_issued(self):
        if self.date_issued and not self.date_expiry and self.document_type_id:
            self.date_expiry = self.document_type_id._ldm_expiry_from(self.date_issued)

    @api.depends("legal_company_id", "document_type_id", "number")
    def _compute_display_name(self):
        for doc in self:
            parts = [doc.document_type_id.name, doc.number, doc.legal_company_id.name]
            doc.display_name = " · ".join(p for p in parts if p) or doc.name or ""

    def _ldm_valid_on(self, on_date):
        """The documents of ``self`` that can be relied on at ``on_date``, the one
        that stays valid longest first. A document that expires never beats one
        with a later expiry; a document without an expiry beats them all."""
        def valid(doc):
            if not doc.active:
                return False
            if doc.date_issued and doc.date_issued > on_date:
                return False
            if doc.date_expiry:
                return doc.date_expiry >= on_date
            if doc.document_type_id.validity in ("fixed_days", "freshness_days") and doc.document_type_id.validity_days:
                return bool(doc.date_issued) and doc.date_issued + timedelta(
                    days=doc.document_type_id.validity_days) >= on_date
            return True
        docs = self.filtered(valid)
        return docs.sorted(lambda d: (d.date_expiry or fields.Date.to_date("9999-12-31"), d.date_issued or on_date,
                                      d.id), reverse=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("date_expiry") and vals.get("date_issued") and vals.get("document_type_id"):
                doc_type = self.env["legal.document.type"].browse(vals["document_type_id"])
                expiry = doc_type._ldm_expiry_from(fields.Date.to_date(vals["date_issued"]))
                if expiry:
                    vals["date_expiry"] = expiry
        docs = super().create(vals_list)
        docs.sudo()._ldm_sync_deadlines()
        return docs

    def write(self, vals):
        result = super().write(vals)
        if {"date_expiry", "active", "legal_company_id", "document_type_id"} & set(vals):
            self.sudo()._ldm_sync_deadlines()
        return result

    def unlink(self):
        self.sudo()._ldm_cancel_deadlines(self.ids)
        return super().unlink()

    # ------------------------------------------------------------------
    # Expiry deadlines
    # ------------------------------------------------------------------
    @api.model
    def _ldm_warning_days(self, company):
        return company.ldm_poa_warning_days or 30

    def _ldm_superseded(self):
        """True when the client holds a newer document of the same type that
        expires later (the old one was renewed by filing a new copy)."""
        self.ensure_one()
        return bool(self.search_count([
            ("id", "!=", self.id), ("legal_company_id", "=", self.legal_company_id.id),
            ("document_type_id", "=", self.document_type_id.id),
            "|", ("date_expiry", "=", False), ("date_expiry", ">", self.date_expiry),
        ], limit=1))

    def _ldm_sync_deadlines(self):
        """Keep exactly one open expiry deadline per document that expires
        within the warning window; close it when the document is renewed,
        archived or no longer expiring. A deadline already met or missed for
        the same expiry date is not opened again. Idempotent: safe to run daily."""
        today = fields.Date.context_today(self)
        Deadline = self.env["legal.deadline"].sudo()
        existing = Deadline.search([("source_model", "=", VAULT), ("source_id", "in", self.ids),
                                    ("state", "!=", "cancelled")])
        by_doc = {}
        for deadline in existing:
            by_doc[deadline.source_id] = by_doc.get(deadline.source_id, Deadline) | deadline
        for doc in self:
            deadlines = by_doc.get(doc.id, Deadline)
            opened = deadlines.filtered(lambda d: d.state in ("open", "awaiting_service"))
            company = doc.company_id or doc.legal_company_id.company_id or self.env.company
            horizon = today + timedelta(days=self._ldm_warning_days(company))
            wanted = bool(doc.active and doc.date_expiry and doc.date_expiry <= horizon)
            if wanted and doc._ldm_superseded():
                opened.write({"state": "done"})
                continue
            if not wanted:
                if opened:
                    renewed = bool(doc.active and doc.date_expiry and doc.date_expiry > horizon)
                    opened.write({"state": "done" if renewed else "cancelled"})
                continue
            values = {
                "name": _("Renew %(document)s of %(client)s", document=doc.document_type_id.name,
                          client=doc.legal_company_id.name),
                "date_safe": doc.date_expiry,
                "date_deadline": doc.date_expiry,
                "note": doc.number or False,
            }
            user = doc.legal_company_id.lawyer_id
            if opened:
                keep, extra = opened[0], opened[1:]
                changed = {k: v for k, v in values.items() if keep[k] != v}
                if keep.user_id != user:
                    changed["user_id"] = user.id or False
                if keep.legal_company_id != doc.legal_company_id:
                    changed["legal_company_id"] = doc.legal_company_id.id
                if changed:
                    keep.write(changed)
                if extra:
                    extra.write({"state": "cancelled"})
            elif not deadlines.filtered(lambda d: d.date_safe == doc.date_expiry):
                values.update({
                    "kind": "expiry",
                    "company_id": company.id,
                    "legal_company_id": doc.legal_company_id.id,
                    "task_id": False,
                    "date_start": doc.date_issued or False,
                    "user_id": user.id or False,
                    "source_model": VAULT,
                    "source_id": doc.id,
                })
                Deadline.create(values)

    @api.model
    def _ldm_cancel_deadlines(self, doc_ids):
        self.env["legal.deadline"].sudo().search([
            ("source_model", "=", VAULT), ("source_id", "in", doc_ids), ("state", "in", ("open", "awaiting_service")),
        ]).write({"state": "cancelled"})

    @api.model
    def _cron_ldm_vault_deadlines(self):
        """Daily: one open deadline per document of the vault that expires soon."""
        docs = self.sudo().with_context(active_test=False).search([
            "|", ("date_expiry", "!=", False), ("id", "in", self._ldm_docs_with_open_deadline()),
        ])
        docs._ldm_sync_deadlines()
        return True

    @api.model
    def _ldm_docs_with_open_deadline(self):
        return self.env["legal.deadline"].sudo().search([
            ("source_model", "=", VAULT), ("state", "in", ("open", "awaiting_service")),
        ]).mapped("source_id")

    def action_open_deadline(self):
        self.ensure_one()
        if not self.deadline_id:
            return False
        return {"type": "ir.actions.act_window", "res_model": "legal.deadline", "res_id": self.deadline_id.id,
                "view_mode": "form", "target": "current"}


class LegalCompany(models.Model):
    _inherit = "legal.company"

    coverage_ids = fields.One2many("legal.company.coverage", "legal_company_id", string="Services this year")

    def action_view_vault(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_company_document")
        action.update({
            "name": _("Documents of %s", self.name),
            "domain": [("legal_company_id", "=", self.id)],
            "context": {"default_legal_company_id": self.id, "search_default_filter_attention": 1},
        })
        return action

    def action_ldm_readiness(self):
        self.ensure_one()
        return self.env["legal.readiness.wizard"]._ldm_open({"default_legal_company_id": self.id})

    # ------------------------------------------------------------------
    # Reminders on the client (no matter to hang them on)
    # ------------------------------------------------------------------
    @api.model
    def _ldm_company_reminder_items(self, company, today):
        """(client, user, date, summary) for documents in the vault that expire
        within the warning window and obligations that are due soon but open
        no matter by themselves. Summaries are in the reminded person's language."""
        items = []
        horizon = today + timedelta(days=company.ldm_poa_warning_days or 30)
        for doc in self.env[VAULT].sudo().search([("company_id", "in", (company.id, False)), ("active", "=", True),
                                                  ("date_expiry", "!=", False), ("date_expiry", "<=", horizon)]):
            if doc._ldm_superseded():
                continue
            user = doc.legal_company_id.lawyer_id
            env = self.with_context(lang=user.lang or self.env.lang).env
            summary = env._("%(document)s expires on %(date)s",
                            document=doc.document_type_id.with_env(env).name,
                            date=format_date(env, doc.date_expiry))
            items.append((doc.legal_company_id, user, doc.date_expiry, summary))
        for obligation in self.env["legal.obligation"].sudo().search([
                ("company_id", "in", (company.id, False)), ("template_id", "=", False), ("next_date", "!=", False)]):
            if obligation.next_date - timedelta(days=obligation.lead_days or 0) > today:
                continue
            user = obligation.legal_company_id.lawyer_id
            env = self.with_context(lang=user.lang or self.env.lang).env
            summary = env._("%(obligation)s is due on %(date)s", obligation=obligation.name,
                            date=format_date(env, obligation.next_date))
            items.append((obligation.legal_company_id, user, obligation.next_date, summary))
        return items

    @api.model
    def _ldm_run_company_reminders(self):
        """One open reminder per (client, person, subject); running it twice changes nothing."""
        activity_type = self.env.ref("legal_department_management.ldm_activity_company_expiry", raise_if_not_found=False)
        Task = self.env["legal.task"]
        for company in self.env["res.company"].search([]):
            calendar = company._ldm_calendar()
            tz = (calendar and calendar.tz) or "Asia/Baghdad"
            today = fields.Date.context_today(self.with_context(tz=tz))
            for client, user, date, summary in self.with_company(company)._ldm_company_reminder_items(company, today):
                if not client.active:
                    continue
                if not user or not user.active or user.share:
                    user = Task._ldm_managers(company)[:1]
                if not user:
                    continue
                existing = client.activity_ids.filtered(
                    lambda a: a.user_id == user and a.summary == summary and a.activity_type_id == activity_type)
                if existing:
                    if existing[0].date_deadline != date:
                        existing[0].sudo().date_deadline = date
                    continue
                client.sudo().activity_schedule(
                    activity_type_id=activity_type.id if activity_type else False,
                    summary=summary, user_id=user.id, date_deadline=date)
        return True

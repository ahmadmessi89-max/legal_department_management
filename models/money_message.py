# -*- coding: utf-8 -*-
"""Ready-written messages to clients (hearing result, hearing reminder,
missing documents, instalment due, statement ready).

They are ``legal.letter.template`` records with ``direction = client``, written
in the client's language, filled from a flat dict of plain strings and sent by
WhatsApp click-to-chat or email. Every use leaves a note in the chatter.
"""
from odoo import _, api, fields, models
from odoo.tools.misc import format_date

from .money_whatsapp import money_text, render_placeholders

CLIENT_CODES = [
    ("hearing_result", "Session result"),
    ("hearing_reminder", "Session reminder"),
    ("missing_documents", "Missing documents"),
    ("instalment_due", "Instalment due"),
    ("statement_ready", "Statement ready"),
]


class LegalLetterTemplate(models.Model):
    _inherit = "legal.letter.template"

    ldm_code = fields.Selection(CLIENT_CODES, string="Used for", index=True,
                                help="Which step offers this message to a client.")

    @api.model
    def _ldm_client_template(self, code):
        if not code:
            return self.browse()
        return self.search([("direction", "=", "client"), ("ldm_code", "=", code)], limit=1)

    @api.model
    def _ldm_client_values(self, lang, task=None, client=None, hearing=None, fee_line=None):
        """The placeholders a client message can use, as plain strings in ``lang``."""
        env = self.with_context(lang=lang).env
        if not task and hearing:
            task = hearing.task_id
        if not task and fee_line:
            task = fee_line.task_id
        task = (task or env["legal.task"]).with_env(env)
        if not client:
            client = task.legal_company_id or (fee_line.engagement_id.legal_company_id if fee_line else False)
        client = (client or env["legal.company"]).with_env(env)
        company = task.company_id or client.company_id or env.company
        values = {
            "client": client.name if client else "",
            "matter": task.name or "",
            "matter_number": task.task_number or "",
            "court": (hearing.department_id.name if hearing else "") or task.department_id.name or "",
            "responsible": task.lawyer_id.name or env.user.name,
            "office": company.name,
            "today": format_date(env, fields.Date.context_today(self)),
            "date": "", "next_date": "", "outcome": "", "needed": "", "documents": "",
            "fee": "", "amount": "", "due_date": "", "balance": "",
        }
        if hearing:
            outcomes = dict(hearing._fields["outcome"]._description_selection(env))
            values["date"] = format_date(env, hearing.date)
            values["outcome"] = outcomes.get(hearing.outcome, "") if hearing.outcome else ""
            upcoming = hearing.next_hearing_id if hearing.state == "held" else hearing
            values["next_date"] = format_date(env, upcoming.date) if upcoming and upcoming.date else ""
            values["needed"] = hearing.needed_before or ""
        elif task:
            planned = task.hearing_ids.filtered(lambda h: h.state == "planned" and h.date).sorted("date")[:1]
            values["next_date"] = format_date(env, planned.date) if planned else ""
        if task:
            missing = task.document_ids.filtered(lambda d: d.mandatory and d.state in ("missing", "expired"))
            values["documents"] = "، ".join(missing.mapped("name")) if lang.startswith("ar") \
                else ", ".join(missing.mapped("name"))
        if fee_line:
            values["fee"] = fee_line.name
            values["amount"] = money_text(env, [(fee_line.currency_id, fee_line.amount)]) or "0"
            values["due_date"] = format_date(env, fee_line.date) if fee_line.date else values["today"]
        if client:
            values["balance"] = money_text(env, [(client.currency_id or company.currency_id,
                                                  client.sudo().balance_due)]) or "0"
        return values

    def _ldm_render_client(self, lang, **records):
        self.ensure_one()
        template = self.with_context(lang=lang)
        return render_placeholders(template.body or "", self._ldm_client_values(lang, **records)).strip()

# -*- coding: utf-8 -*-
"""Send a client a ready-written message by WhatsApp (click-to-chat, no API)
or by email. The text is filled in the client's language and stays editable;
every use leaves a note in the matter's (or client's) chatter."""
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..models.money_whatsapp import normalize_iraqi_phone, wa_link


class LegalClientMessageWizard(models.TransientModel):
    _name = "legal.client.message.wizard"
    _description = "Message to a client"

    template_id = fields.Many2one("legal.letter.template", string="Message", domain=[("direction", "=", "client")])
    task_id = fields.Many2one("legal.task", string="Matter")
    legal_company_id = fields.Many2one("legal.company", string="Client")
    hearing_id = fields.Many2one("legal.hearing", string="Court session")
    fee_line_id = fields.Many2one("legal.engagement.line", string="Instalment")
    partner_id = fields.Many2one("res.partner", string="To")
    phone = fields.Char(string="WhatsApp number")
    email = fields.Char(related="partner_id.email", string="Email")
    lang = fields.Selection(lambda self: self.env["res.lang"].get_installed(), string="Language")
    body = fields.Text(string="Text", compute="_compute_body", store=True, readonly=False)
    phone_ok = fields.Boolean(compute="_compute_phone")
    wa_url = fields.Char(compute="_compute_phone")

    @api.model
    def ldm_open(self, code, task=None, client=None, hearing=None, fee_line=None):
        """Open the dialog with the template for ``code`` (see money_message.CLIENT_CODES)."""
        if not self.env["legal.task"]._ldm_feature("group_ldm_client_messages"):
            raise UserError(_("Messages to clients are switched off in Settings."))
        if not self.env.user.has_group("legal_department_management.group_ldm_clerk") \
                and not self.env.user.has_group("legal_department_management.group_ldm_billing_user"):
            raise AccessError(_("Only the legal team can message clients."))
        task = task or (hearing.task_id if hearing else None) or (fee_line.task_id if fee_line else None)
        client = client or (task.legal_company_id if task else None) or \
            (fee_line.engagement_id.legal_company_id if fee_line else None)
        template = self.env["legal.letter.template"]._ldm_client_template(code)
        return {
            "type": "ir.actions.act_window",
            "name": _("Message the client"),
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_template_id": template.id or False,
                "default_task_id": task.id if task else False,
                "default_legal_company_id": client.id if client else False,
                "default_hearing_id": hearing.id if hearing else False,
                "default_fee_line_id": fee_line.id if fee_line else False,
            },
        }

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        client = self.env["legal.company"].browse(values.get("legal_company_id")).exists()
        partner = client.partner_id
        if partner:
            values.setdefault("partner_id", partner.id)
            values.setdefault("phone", partner.phone or False)
            values.setdefault("lang", partner.lang or "ar_001")
        values.setdefault("lang", "ar_001" if self.env["res.lang"]._lang_get("ar_001") else self.env.lang)
        return values

    @api.depends("template_id", "lang", "task_id", "hearing_id", "fee_line_id", "legal_company_id")
    def _compute_body(self):
        for wizard in self:
            if not wizard.template_id:
                wizard.body = wizard.body or False
                continue
            wizard.body = wizard.template_id._ldm_render_client(
                wizard.lang or "ar_001", task=wizard.task_id or None, client=wizard.legal_company_id or None,
                hearing=wizard.hearing_id or None, fee_line=wizard.fee_line_id or None)

    @api.depends("phone", "body")
    def _compute_phone(self):
        for wizard in self:
            wizard.phone_ok = bool(normalize_iraqi_phone(wizard.phone))
            wizard.wa_url = wa_link(wizard.phone, wizard.body or "") or False

    def _ldm_log(self, channel):
        record = self.task_id or self.legal_company_id
        if not record:
            return
        record.sudo().message_post(
            body=Markup("%s<br/>%s") % (_("Message sent to the client by %(channel)s (%(to)s):", channel=channel,
                                          to=self.phone if channel == "WhatsApp" else (self.email or "")),
                                        self.body or ""),
            message_type="comment", subtype_xmlid="mail.mt_note")

    def action_whatsapp(self):
        self.ensure_one()
        if not (self.body or "").strip():
            raise UserError(_("Write the message first."))
        if not self.phone_ok:
            raise UserError(_("%s is not a phone number WhatsApp can reach. Enter it as 07XX XXX XXXX or with +964.",
                              self.phone or _("The number")))
        self._ldm_log("WhatsApp")
        return {"type": "ir.actions.act_url", "url": self.wa_url, "target": "new"}

    def action_email(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(_("The client has no email address. Add it on the client, or send by WhatsApp."))
        if not (self.body or "").strip():
            raise UserError(_("Write the message first."))
        record = (self.task_id or self.legal_company_id).sudo()
        # The sent email is itself the chatter entry.
        record.message_post(body=self.body, partner_ids=self.partner_id.ids, message_type="comment",
                            subtype_xmlid="mail.mt_comment",
                            subject=self.template_id.with_context(lang=self.lang).subject or False)
        return {"type": "ir.actions.act_window_close"}

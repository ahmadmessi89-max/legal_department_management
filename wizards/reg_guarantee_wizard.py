# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.reg_render import placeholder_values

TEMPLATES = {
    "request_extension": "legal_department_management.ldm_letter_guarantee_extension",
    "release": "legal_department_management.ldm_letter_guarantee_release",
}


def _default_letter_lang(model):
    return "ar_001" if model.env["res.lang"]._lang_get("ar_001") else model.env.lang


class LegalGuaranteeWizard(models.TransientModel):
    """Ask the bank to extend, record the extension, or release a letter of
    guarantee; the letter to the bank or the beneficiary is drafted from a
    template."""

    _name = "legal.guarantee.wizard"
    _description = "Act on a letter of guarantee"

    guarantee_id = fields.Many2one("legal.guarantee", string="Letter of guarantee", required=True, ondelete="cascade")
    mode = fields.Selection([("request_extension", "Ask the bank to extend"), ("extend", "Record the extension"),
                             ("release", "Release")], required=True, default="request_extension")
    current_expiry = fields.Date(related="guarantee_id.date_expiry", string="Expires on")
    new_expiry = fields.Date(string="New expiry date")
    date = fields.Date(string="Date", default=fields.Date.context_today)
    draft_letter = fields.Boolean(string="Draft the letter", default=True)
    template_id = fields.Many2one("legal.letter.template", string="Letter template")
    lang = fields.Selection(lambda self: self.env["res.lang"].get_installed(), string="Letter language",
                            default=_default_letter_lang)
    note = fields.Text(string="Note")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        xmlid = TEMPLATES.get(values.get("mode") or self.env.context.get("default_mode"))
        if xmlid and "template_id" in fields_list and not values.get("template_id"):
            template = self.env.ref(xmlid, raise_if_not_found=False)
            values["template_id"] = template.id if template else False
        if values.get("mode") == "extend":
            values["draft_letter"] = False
        return values

    def action_confirm(self):
        self.ensure_one()
        guarantee = self.guarantee_id
        guarantee.check_access("write")
        letter = self.env["legal.correspondence"]
        if self.mode == "extend":
            if not self.new_expiry or (guarantee.date_expiry and self.new_expiry <= guarantee.date_expiry):
                raise UserError(_("Enter the new expiry date the bank gave: it must be after %s.",
                                  guarantee.date_expiry))
            old = guarantee.date_expiry
            guarantee.write({"date_expiry": self.new_expiry, "state": "extended"})
            guarantee.message_post(body=_("Extended from %(old)s to %(new)s. %(note)s", old=old, new=self.new_expiry,
                                          note=self.note or ""))
        elif self.mode == "request_extension":
            guarantee.write({"state": "extension_requested"})
            guarantee.message_post(body=_("Extension requested from the bank. %s", self.note or ""))
            if self.draft_letter:
                letter = self._ldm_draft_letter(guarantee.bank_id)
        else:
            guarantee.write({"state": "released", "release_date": self.date})
            guarantee.message_post(body=_("Released on %(date)s. %(note)s", date=self.date, note=self.note or ""))
            if self.draft_letter:
                letter = self._ldm_draft_letter(guarantee.beneficiary_id)
        if letter:
            return {"type": "ir.actions.act_window", "res_model": "legal.correspondence", "res_id": letter.id,
                    "view_mode": "form", "target": "current"}
        return {"type": "ir.actions.act_window_close"}

    def _ldm_draft_letter(self, addressee):
        if not self.template_id:
            raise UserError(_("Choose the letter template, or untick “Draft the letter”."))
        guarantee = self.guarantee_id
        values = placeholder_values(self.env, guarantee=guarantee, partner=addressee, lang=self.lang)
        subject, body = self.template_id.ldm_render(values, lang=self.lang)
        return self.env["legal.correspondence"]._ldm_create_document({
            "name": subject or self.template_id.name,
            "template_id": self.template_id.id,
            "body_html": body,
            "lang": self.lang,
            "partner_id": addressee.id or False,
            "guarantee_id": guarantee.id,
            "legal_company_id": guarantee.legal_company_id.id or False,
            "signatory_id": self.env.user.id,
        })

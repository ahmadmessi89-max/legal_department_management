# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import is_html_empty

from ..models.reg_render import placeholder_values


def _installed_langs(model):
    return model.env["res.lang"].get_installed()


def _default_letter_lang(model):
    return "ar_001" if model.env["res.lang"]._lang_get("ar_001") else model.env.lang


class LegalCorrespondenceVoidWizard(models.TransientModel):
    _name = "legal.correspondence.void.wizard"
    _description = "Void a letter"

    correspondence_id = fields.Many2one("legal.correspondence", string="Letter", required=True, ondelete="cascade")
    reason = fields.Text(string="Why is it void?", required=True,
                         help="The number stays in the book, struck through, with this reason next to it.")

    def action_confirm(self):
        self.ensure_one()
        self.correspondence_id._ldm_void(self.reason)
        return {"type": "ir.actions.act_window_close"}


class LegalDocumentWizard(models.TransientModel):
    """New document from a template: the text is filled from the matter (or
    the letter of guarantee, or the power of attorney), can be edited here,
    and becomes a letter with its PDF filed on the matter."""

    _name = "legal.document.wizard"
    _description = "New document from a template"

    task_id = fields.Many2one("legal.task", string="Matter", ondelete="cascade")
    guarantee_id = fields.Many2one("legal.guarantee", string="Letter of guarantee", ondelete="cascade")
    poa_id = fields.Many2one("legal.poa", string="Power of attorney", ondelete="cascade")
    template_id = fields.Many2one("legal.letter.template", string="Template", required=True)
    lang = fields.Selection(_installed_langs, string="Language", required=True, default=_default_letter_lang)
    department_id = fields.Many2one("legal.department", string="To (body)")
    partner_id = fields.Many2one("res.partner", string="To (person or company)")
    subject = fields.Char(string="Subject")
    body_html = fields.Html(string="Text", sanitize_style=True)
    signatory_id = fields.Many2one("res.users", string="Signed by", default=lambda self: self.env.user)
    signatory_title = fields.Char(string="Signatory title")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        task = self.env["legal.task"].browse(values.get("task_id")) if values.get("task_id") else False
        if task and "department_id" in fields_list and not values.get("department_id"):
            values["department_id"] = task.department_id.id or False
        return values

    @api.onchange("template_id", "lang", "department_id", "partner_id", "task_id", "signatory_id",
                  "signatory_title")
    def _onchange_render(self):
        if not self.template_id:
            return
        values = placeholder_values(self.env, task=self.task_id, guarantee=self.guarantee_id, poa=self.poa_id,
                                    body=self.department_id, partner=self.partner_id, lang=self.lang)
        values["signatory"] = self.signatory_id.name or ""
        values["signatory_title"] = self.signatory_title or ""
        subject, body = self.template_id.ldm_render(values, lang=self.lang)
        self.subject = subject or self.subject
        self.body_html = body

    def action_create(self):
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("Choose a template."))
        if is_html_empty(self.body_html):
            self._onchange_render()
        letter = self.env["legal.correspondence"]._ldm_create_document({
            "name": self.subject or self.template_id.name,
            "template_id": self.template_id.id,
            "body_html": self.body_html,
            "lang": self.lang,
            "task_id": self.task_id.id or False,
            "department_id": self.department_id.id or False,
            "partner_id": self.partner_id.id or False,
            "guarantee_id": self.guarantee_id.id or False,
            "poa_id": self.poa_id.id or False,
            "signatory_id": self.signatory_id.id or False,
            "signatory_title": self.signatory_title or False,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "legal.correspondence",
            "res_id": letter.id,
            "view_mode": "form",
            "target": "current",
        }


class LegalRegisterBookWizard(models.TransientModel):
    _name = "legal.register.book.wizard"
    _description = "Print the correspondence register book"

    date_from = fields.Date(string="From", required=True,
                            default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)
    direction = fields.Selection([("both", "Incoming and outgoing"), ("incoming", "Incoming only"),
                                  ("outgoing", "Outgoing only")], string="Books", required=True, default="both")

    def action_print(self):
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(_("The end date is before the start date."))
        data = {"date_from": fields.Date.to_string(self.date_from), "date_to": fields.Date.to_string(self.date_to),
                "direction": self.direction}
        return self.env.ref("legal_department_management.action_report_ldm_register_book").report_action(
            [], data=data, config=False)

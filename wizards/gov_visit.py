# -*- coding: utf-8 -*-
"""The counter-visit dialog (SPEC 5.8 and 14.4).

A runner at a government counter records, from a phone, what happened: done,
still pending or rejected; the receipt number; the fee paid and a photo of the
receipt; what comes next and when; what the body is waiting for. One
confirmation updates the step, creates exactly one expense line when a fee was
paid, hands the matter to whoever holds the ball, and writes one line in the
matter's history.
"""
from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

RESULTS = [("done", "Done"), ("pending", "Still pending"), ("rejected", "Rejected")]


class LegalVisitWizard(models.TransientModel):
    _name = "legal.visit.wizard"
    _description = "Log a counter visit"

    task_id = fields.Many2one("legal.task", string="Matter", required=True, ondelete="cascade")
    step_id = fields.Many2one("legal.task.step", string="Planned visit", ondelete="cascade",
                              domain="[('task_id', '=', task_id), ('is_visit', '=', True), ('state', '=', 'todo')]")
    department_id = fields.Many2one("legal.department", string="Body", compute="_compute_department_id",
                                    store=True, readonly=False, precompute=True)
    visit_name = fields.Char(string="Visit", compute="_compute_visit_name", store=True, readonly=False,
                             precompute=True)
    result = fields.Selection(RESULTS, string="Result", required=True, default="done")
    visit_date = fields.Date(string="Date of the visit", required=True, default=fields.Date.context_today)
    receipt_number = fields.Char(string="Receipt number")
    fee_amount = fields.Monetary(string="Fee paid", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="Currency", required=True,
                                  compute="_compute_currency_id", store=True, readonly=False,
                                  precompute=True)
    photo = fields.Binary(string="Photo of the receipt", attachment=False)
    photo_name = fields.Char(string="Photo name")
    next_step = fields.Char(string="Next step")
    next_date = fields.Date(string="Next visit on")
    waiting_for = fields.Char(string="The body is waiting for",
                              help="What must be brought or answered before the body continues, e.g. the tax clearance letter.")
    waiting_on = fields.Selection(
        [("body", "The body"), ("us", "Us"), ("client", "The client")],
        string="Now waiting on", compute="_compute_waiting_on", store=True, readonly=False, precompute=True,
        help="Who has to act next. While the body has the file, the days at the body are counted.")
    note = fields.Char(string="Note")

    @api.model
    def _ldm_open(self, context):
        return {
            "type": "ir.actions.act_window",
            "name": _("Log a visit"),
            "res_model": "legal.visit.wizard",
            "view_mode": "form",
            "views": [(self.env.ref("legal_department_management.view_legal_visit_wizard_form").id, "form")],
            "target": "new",
            "context": dict(context, dialog_size="medium"),
        }

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        context = self.env.context
        if not values.get("step_id") and context.get("active_model") == "legal.task.step" and context.get("active_id"):
            values["step_id"] = context["active_id"]
        if values.get("step_id") and not values.get("task_id"):
            values["task_id"] = self.env["legal.task.step"].browse(values["step_id"]).task_id.id
        if not values.get("task_id") and context.get("active_model") == "legal.task" and context.get("active_id"):
            values["task_id"] = context["active_id"]
        return values

    @api.depends("step_id", "task_id")
    def _compute_department_id(self):
        for wizard in self:
            wizard.department_id = wizard.step_id.department_id or wizard.task_id.department_id

    @api.depends("step_id", "department_id")
    def _compute_visit_name(self):
        for wizard in self:
            if wizard.step_id:
                wizard.visit_name = wizard.step_id.name
            elif not wizard.visit_name:
                wizard.visit_name = (_("Visit to %s", wizard.department_id.name) if wizard.department_id
                                     else _("Visit to the body"))

    @api.depends("task_id")
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.task_id.currency_id or self.env.company.currency_id

    @api.depends("result", "step_id", "task_id", "next_step", "next_date")
    def _compute_waiting_on(self):
        """Turned away: the ball is ours. Pending: the body has it. Done: the
        body has it while more visits are planned, otherwise it is back with us."""
        for wizard in self:
            if wizard.result == "rejected":
                wizard.waiting_on = "us"
            elif wizard.result == "pending":
                wizard.waiting_on = "body"
            else:
                later = wizard.task_id.step_ids.filtered(
                    lambda s: s.is_visit and s.state == "todo" and s != wizard.step_id._origin)
                wizard.waiting_on = "body" if (later or wizard.next_step or wizard.next_date) else "us"

    # ------------------------------------------------------------------
    def action_confirm(self):
        self.ensure_one()
        task = self.task_id
        if task.state in ("done", "cancelled"):
            raise UserError(_("%s is closed; reopen it before logging a visit.", task.display_name))
        if not self.env.user.has_group("legal_department_management.group_ldm_clerk"):
            raise UserError(_("Only the legal team can log a visit."))
        if self.fee_amount < 0:
            raise UserError(_("The fee cannot be negative."))
        if self.step_id and (self.step_id.task_id != task or not self.step_id.is_visit):
            raise UserError(_("Choose a visit of %s.", task.display_name))
        if self.step_id and self.step_id.state != "todo":
            raise UserError(_("“%s” is already done.", self.step_id.name))
        task.check_access("write")

        step = self.step_id or self.env["legal.task.step"].create({
            "task_id": task.id,
            "name": self.visit_name or _("Visit to the body"),
            "is_visit": True,
            "department_id": self.department_id.id or False,
            "date_due": self.visit_date,
            "user_id": self.env.user.id,
            "sequence": max(task.step_ids.mapped("sequence") or [0]) + 1,
        })

        attachment = self.env["ir.attachment"]
        if self.photo:
            attachment = attachment.create({
                "name": self.photo_name or _("Receipt %s", self.receipt_number or step.name),
                "datas": self.photo,
                "res_model": "legal.task",
                "res_id": task.id,
            })

        fee_in_task_currency = self.fee_amount
        if self.fee_amount and self.currency_id != task.currency_id:
            fee_in_task_currency = self.currency_id._convert(self.fee_amount, task.currency_id, task.company_id,
                                                             self.visit_date)
        step_values = {
            "visit_result": self.result,
            "visit_waiting_for": self.waiting_for or False,
            "department_id": step.department_id.id or self.department_id.id or False,
        }
        if self.receipt_number:
            step_values["receipt_number"] = self.receipt_number
        if self.fee_amount:
            step_values["fee_amount"] = (step.fee_amount or 0.0) + fee_in_task_currency
        if attachment:
            step_values["attachment_id"] = attachment.id
        if self.note:
            step_values["note"] = self.note
        if self.result == "done":
            step_values.update({"state": "done", "done_date": self.visit_date, "done_by_id": self.env.user.id})
        elif self.next_date:
            # Still pending or turned away: the same visit, on a new date.
            step_values["date_due"] = self.next_date
        step.write(step_values)

        expense = self.env["legal.task.expense"]
        if self.fee_amount:
            expense = expense.create({
                "task_id": task.id,
                "date": self.visit_date,
                "category_id": self.env["legal.expense.category"]._ldm_government_fee().id,
                "name": _("Fee: %s", step.name),
                "amount": self.fee_amount,
                "currency_id": self.currency_id.id,
                "receipt_number": self.receipt_number or False,
                "attachment_id": attachment.id or False,
                "step_id": step.id,
            })

        next_step = self.env["legal.task.step"]
        if self.result == "done" and (self.next_step or self.next_date):
            next_step = next_step.create({
                "task_id": task.id,
                "name": self.next_step or _("Follow up at %s", step.department_id.name or _("the body")),
                "is_visit": True,
                "department_id": step.department_id.id or False,
                "date_due": self.next_date or False,
                "user_id": self.env.user.id,
                "sequence": step.sequence + 1,
            })

        task._ldm_set_waiting_on(self.waiting_on, self.visit_date)
        task.message_post(body=self._ldm_history_line(step, expense, next_step), subtype_xmlid="mail.mt_note",
                          attachment_ids=attachment.ids)
        return {"type": "ir.actions.act_window_close"}

    def _ldm_history_line(self, step, expense, next_step):
        results = dict(self._fields["result"]._description_selection(self.env))
        lines = [_("Visit %(visit)s at %(body)s: %(result)s.", visit=step.name,
                   body=step.department_id.name or _("the body"), result=results[self.result])]
        if self.receipt_number:
            lines.append(_("Receipt number: %s", self.receipt_number))
        if expense:
            lines.append(_("Fee paid: %s", self.currency_id.format(self.fee_amount)))
        if self.waiting_for:
            lines.append(_("The body is waiting for: %s", self.waiting_for))
        if next_step:
            if self.next_date:
                lines.append(_("Next: %(step)s on %(date)s", step=next_step.name, date=format_date(self.env, self.next_date)))
            else:
                lines.append(_("Next: %s", next_step.name))
        elif self.next_date:
            lines.append(_("Back at the counter on %s", format_date(self.env, self.next_date)))
        if self.note:
            lines.append(self.note)
        return Markup("<br/>").join(escape(line) for line in lines)

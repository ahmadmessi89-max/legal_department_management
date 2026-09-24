# -*- coding: utf-8 -*-
"""One-click completion of a matter's steps, with Undo (SPEC 14.4).

The checklist on the cockpit and the rows on My Day tick a step in one click.
The click is forgiven for a few seconds: Undo puts the step back and removes
the expense line the same click created for a paid counter visit, and nothing
else. Everything is decided here, so a tick from the browser, from a test or
from another stream obeys the same rules.
"""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .ws_common import CLOSED_STATES

# An Undo is offered for six seconds; the server accepts it for longer so a slow
# connection does not turn a click on Undo into an error.
UNDO_WINDOW = timedelta(minutes=15)


class LegalTaskStep(models.Model):
    _inherit = "legal.task.step"

    def _ldm_check_can_tick(self):
        for step in self:
            step.check_access("write")
            if step.task_id.state in CLOSED_STATES:
                raise UserError(_("%s is closed: reopen it before changing its steps.", step.task_id.display_name))

    @api.model
    def _ldm_government_fee_category(self):
        """The expense category a paid counter visit is booked under, when the
        money stream has shipped one. Found by code first, then by name."""
        Category = self.env["legal.expense.category"]
        category = Category.search([("code", "in", ("government_fee", "GOV_FEE", "gov_fee", "GOV"))], limit=1)
        if not category:
            category = Category.search([("name", "ilike", "government")], limit=1)
        return category

    def action_ldm_toggle_done(self):
        """Tick the step, or untick it when it is already done.

        Returns what the browser needs to offer Undo: the new state and the ids
        of the expense lines this very click created (a done counter visit with
        a fee books one expense line, once)."""
        self.ensure_one()
        self._ldm_check_can_tick()
        step = self
        if step.state != "todo":
            step.write({"state": "todo", "done_date": False, "done_by_id": False})
            return {"state": "todo", "expense_ids": [], "message": _("“%s” is open again.", step.name)}
        step.write({
            "state": "done",
            "done_date": fields.Date.context_today(step),
            "done_by_id": self.env.uid,
        })
        expenses = step._ldm_book_visit_fee()
        step._ldm_close_reminder()
        return {"state": "done", "expense_ids": expenses.ids, "message": _("“%s” is done.", step.name)}

    def action_ldm_undo_done(self, expense_ids=None):
        """Undo a tick: the step is open again and the expense line booked by
        that tick is removed. Only lines of this step, created by this user in
        the last minutes, are touched; anything else stays."""
        self.ensure_one()
        self._ldm_check_can_tick()
        self.write({"state": "todo", "done_date": False, "done_by_id": False})
        if expense_ids:
            since = fields.Datetime.now() - UNDO_WINDOW
            expenses = self.env["legal.task.expense"].browse(expense_ids).exists().filtered(
                lambda e: e.step_id == self and e.create_uid == self.env.user and e.create_date >= since)
            # Deleting an expense is a manager's right; removing the one this
            # user's own click created a moment ago is not a deletion of record.
            expenses.sudo().unlink()
        return True

    def _ldm_book_visit_fee(self):
        """A done counter visit with a fee creates exactly one expense line."""
        self.ensure_one()
        Expense = self.env["legal.task.expense"]
        if not (self.is_visit and self.fee_amount) or self.expense_ids:
            return Expense
        category = self._ldm_government_fee_category()
        return Expense.create({
            "task_id": self.task_id.id,
            "step_id": self.id,
            "date": self.done_date or fields.Date.context_today(self),
            "name": self.name,
            "amount": self.fee_amount,
            "currency_id": (self.currency_id or self.task_id.currency_id).id,
            "receipt_number": self.receipt_number or False,
            "category_id": category.id or False,
            "attachment_id": self.attachment_id.id or False,
            "paid_by": "office",
        })

    def _ldm_close_reminder(self):
        """Completing a step closes the reminder the cron wrote for it."""
        activity_type = self.env.ref("legal_department_management.ldm_activity_step", raise_if_not_found=False)
        if not activity_type:
            return
        for step in self:
            activities = step.task_id.activity_ids.filtered(
                lambda a, s=step: a.activity_type_id == activity_type and a.summary and s.name in a.summary)
            if activities:
                activities.sudo().action_feedback(feedback=_("Done"))

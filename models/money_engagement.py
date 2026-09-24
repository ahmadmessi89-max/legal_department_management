# -*- coding: utf-8 -*-
"""Fee agreements (عقد الأتعاب) and their schedule.

The law this encodes (research 04 §4.3-4.4):
- Advocacy Law Art. 56(1): outside criminal matters, the fee may not exceed
  20% of the value of the work. Fixed fee + success % x value is checked against
  20% of the value of the linked non-criminal matters, in the agreement's
  currency; activating an agreement above the cap needs a legal manager and a
  reason.
- Art. 58: settling or ending the matter early still entitles the lawyer to the
  fee, so the close dialog proposes the remaining instalments.
- Bar administrative order 3021 of 2021: a company's legal-adviser retainer has a
  monthly minimum (local / foreign company), paid a year in advance, with a 5%
  Bar share withheld by the company.
"""
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

from .money_whatsapp import money_text

MANAGER = "legal_department_management.group_legal_manager"
FIXED_TYPES = ("lump_sum", "installments", "consultation", "success")
CAP_RATE = 0.20


class LegalEngagement(models.Model):
    _inherit = "legal.engagement"

    name = fields.Char(default=lambda self: _("New"), copy=False)
    company_currency_id = fields.Many2one(related="company_id.currency_id", string="Company currency")
    task_count = fields.Integer(string="Number of matters", compute="_compute_task_count")

    cap_applies = fields.Boolean(string="20% cap applies", compute="_compute_cap")
    cap_exempt = fields.Boolean(string="Criminal matters only", compute="_compute_cap")
    cap_base = fields.Monetary(string="Value of the matters", currency_field="currency_id", compute="_compute_cap")
    cap_limit = fields.Monetary(string="20% of the value", currency_field="currency_id", compute="_compute_cap")
    cap_fee = fields.Monetary(string="Fee against the cap", currency_field="currency_id", compute="_compute_cap")
    cap_exceeded = fields.Boolean(string="Above the 20% cap", compute="_compute_cap")

    retainer_minimum = fields.Monetary(string="Bar minimum per month", currency_field="company_currency_id",
                                       compute="_compute_retainer_minimum")
    retainer_below_minimum = fields.Boolean(string="Below the Bar minimum", compute="_compute_retainer_minimum")

    amount_scheduled = fields.Monetary(string="Scheduled", currency_field="currency_id", compute="_compute_totals")
    amount_invoiced = fields.Monetary(string="Invoiced", currency_field="currency_id", compute="_compute_totals")
    amount_due = fields.Monetary(string="Due now", currency_field="currency_id", compute="_compute_totals")
    amount_planned = fields.Monetary(string="Still to come", currency_field="currency_id", compute="_compute_totals")
    next_line_text = fields.Char(string="Next instalment", compute="_compute_totals")
    ldm_is_manager = fields.Boolean(compute="_compute_ldm_is_manager")
    ldm_can_message = fields.Boolean(compute="_compute_ldm_is_manager")
    signed_copy = fields.Binary(string="Signed agreement (scan)", attachment=True, copy=False)
    signed_copy_name = fields.Char(string="Signed copy file name", copy=False)

    def _compute_task_count(self):
        for engagement in self:
            engagement.task_count = len(engagement.task_ids)

    @api.depends_context("uid")
    def _compute_ldm_is_manager(self):
        is_manager = self.env.user.has_group(MANAGER)
        can_message = self.env["legal.task"]._ldm_user_can_message()
        for engagement in self:
            engagement.ldm_is_manager = is_manager
            engagement.ldm_can_message = can_message

    @api.depends("fee_type", "amount", "success_percent", "currency_id", "date_start", "company_id",
                 "task_ids.matter_value", "task_ids.currency_id", "task_ids.law_branch", "line_ids.amount",
                 "line_ids.trigger_event", "line_ids.state")
    def _compute_cap(self):
        today = fields.Date.context_today(self)
        for engagement in self:
            currency = engagement.currency_id or engagement.company_id.currency_id
            matters = engagement.task_ids.filtered(lambda t: t.law_branch != "criminal")
            day = engagement.date_start or today
            base = sum(t.currency_id._convert(t.matter_value, currency, engagement.company_id, day)
                       for t in matters if t.matter_value)
            fee = engagement._ldm_fixed_fee() + (engagement.success_percent or 0.0) / 100.0 * base
            applies = engagement.fee_type in FIXED_TYPES or bool(engagement.success_percent)
            engagement.cap_exempt = bool(engagement.task_ids) and not matters
            engagement.cap_base = base
            engagement.cap_limit = CAP_RATE * base
            engagement.cap_fee = fee
            engagement.cap_applies = bool(applies and base)
            engagement.cap_exceeded = bool(
                applies and base and engagement.company_id.ldm_fee_cap_check
                and currency.compare_amounts(fee, CAP_RATE * base) > 0)

    def _ldm_fixed_fee(self):
        """The fixed part of the fee, in the agreement's currency."""
        self.ensure_one()
        if self.fee_type not in FIXED_TYPES:
            return 0.0
        scheduled = sum(line.amount for line in self.line_ids
                        if line.state != "waived" and line.trigger_event != "collection")
        return max(self.amount or 0.0, scheduled)

    @api.depends("fee_type", "amount", "currency_id", "date_start", "legal_company_id.company_type",
                 "legal_company_id.client_kind", "company_id.ldm_retainer_min_local",
                 "company_id.ldm_retainer_min_foreign")
    def _compute_retainer_minimum(self):
        today = fields.Date.context_today(self)
        for engagement in self:
            company = engagement.company_id or self.env.company
            foreign = engagement.legal_company_id.company_type == "foreign_branch"
            minimum = company.ldm_retainer_min_foreign if foreign else company.ldm_retainer_min_local
            engagement.retainer_minimum = minimum
            below = False
            if engagement.fee_type == "retainer" and engagement.legal_company_id.client_kind == "company" and minimum:
                monthly = (engagement.currency_id or company.currency_id)._convert(
                    engagement.amount or 0.0, company.currency_id, company, engagement.date_start or today)
                below = company.currency_id.compare_amounts(monthly, minimum) < 0
            engagement.retainer_below_minimum = below

    @api.depends("line_ids.amount", "line_ids.state", "line_ids.date", "line_ids.name", "line_ids.trigger_event")
    def _compute_totals(self):
        triggers = dict(self.env["legal.engagement.line"]._fields["trigger_event"]._description_selection(self.env))
        for engagement in self:
            lines = engagement.line_ids.filtered(lambda l: l.state != "waived")
            engagement.amount_scheduled = sum(lines.mapped("amount"))
            engagement.amount_invoiced = sum(lines.filtered(lambda l: l.state in ("invoiced", "paid")).mapped("amount"))
            engagement.amount_due = sum(lines.filtered(lambda l: l.state == "due").mapped("amount"))
            planned = lines.filtered(lambda l: l.state == "planned")
            engagement.amount_planned = sum(planned.mapped("amount"))
            upcoming = (lines.filtered(lambda l: l.state == "due") or planned)[:1]
            if upcoming:
                when = format_date(self.env, upcoming.date) if upcoming.trigger_event == "date" and upcoming.date \
                    else triggers.get(upcoming.trigger_event, "")
                engagement.next_line_text = _("%(name)s: %(amount)s, %(when)s", name=upcoming.name,
                                              amount=money_text(self.env, [(engagement.currency_id, upcoming.amount)]) or "0",
                                              when=when)
            else:
                engagement.next_line_text = False

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") in ("New", _("New")):
                company = self.env["res.company"].browse(vals.get("company_id")) if vals.get("company_id") \
                    else self.env.company
                vals["name"] = self.env["ir.sequence"].with_company(company).next_by_code("legal.engagement") or _("New")
            if vals.get("fee_type") == "retainer" and not vals.get("retainer_period"):
                vals["retainer_period"] = "monthly"
            if vals.get("signed") and not vals.get("signed_date"):
                vals["signed_date"] = fields.Date.context_today(self)
        engagements = super().create(vals_list)
        activating = engagements.filtered(lambda e: e.state == "active")
        if activating:
            activating._ldm_check_activation()
            activating._ldm_on_activate()
        return engagements

    def write(self, vals):
        if vals.get("signed") and "signed_date" not in vals:
            vals = dict(vals, signed_date=fields.Date.context_today(self))
        activating = self.filtered(lambda e: e.state != "active") if vals.get("state") == "active" else self.browse()
        newly_signed = self.filtered(lambda e: not e.signed) if vals.get("signed") else self.browse()
        if vals.get("state") == "draft" and not self.env.su and not self.env.user.has_group(MANAGER):
            if any(e.state != "draft" for e in self):
                raise UserError(_("Only a legal manager can send a fee agreement back to draft."))
        result = super().write(vals)
        if "signed_copy" in vals:
            self._ldm_link_signed_copy()
        if activating:
            activating._ldm_check_activation()
            activating._ldm_on_activate()
        for engagement in newly_signed.filtered(lambda e: e.state == "active"):
            engagement._ldm_fire("signing")
        return result

    def _ldm_link_signed_copy(self):
        """Keep the foundation's ``attachment_id`` pointing at the uploaded signed copy."""
        for engagement in self:
            attachment = self.env["ir.attachment"].sudo().search([
                ("res_model", "=", self._name), ("res_id", "=", engagement.id), ("res_field", "=", "signed_copy")],
                limit=1)
            super(LegalEngagement, engagement).write({"attachment_id": attachment.id or False})
            if attachment and not engagement.signed:
                engagement.write({"signed": True})

    def unlink(self):
        if any(e.state != "draft" for e in self) and not self.env.su:
            raise UserError(_("Only a draft fee agreement can be deleted. Close it instead."))
        if self.task_ids and not self.env.su:
            raise UserError(_("This fee agreement covers matters. Remove it from them or close it."))
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _ldm_check_activation(self):
        for engagement in self:
            if engagement.fee_type == "hourly" and not engagement.hourly_rate:
                raise UserError(_("Enter the hourly rate of %s before activating it.", engagement.name))
            if engagement.fee_type == "success" and not engagement.success_percent:
                raise UserError(_("Enter the success fee percentage of %s before activating it.", engagement.name))
            if engagement.fee_type not in ("hourly", "success") and not engagement.amount and not engagement.line_ids:
                raise UserError(_("Enter the agreed fee of %s before activating it.", engagement.name))
            if engagement.cap_exceeded:
                if not (self.env.su or self.env.user.has_group(MANAGER)):
                    raise UserError(_(
                        "The fee of %(name)s is above 20%% of the value of its matters (Advocacy Law Art. 56). "
                        "Only a legal manager can activate it.", name=engagement.name))
                if not (engagement.cap_override_reason or "").strip():
                    raise UserError(_("Say why the fee of %s may exceed 20%% of the value before activating it.",
                                      engagement.name))

    def _ldm_on_activate(self):
        for engagement in self:
            engagement._ldm_generate_retainer_lines()
            if engagement.signed:
                engagement._ldm_fire("signing")
            engagement._ldm_due_dated_lines()
            if engagement.cap_exceeded:
                engagement.message_post(body=_("Activated above the 20%% cap by %(user)s: %(reason)s",
                                               user=self.env.user.name, reason=engagement.cap_override_reason))
            else:
                engagement.message_post(body=_("Fee agreement activated."))

    def action_ldm_activate(self):
        self.write({"state": "active"})
        return True

    def action_ldm_close(self):
        self.write({"state": "closed", "date_end": fields.Date.context_today(self)})
        return True

    def action_ldm_reset(self):
        self.write({"state": "draft"})
        return True

    def action_ldm_print(self):
        return self.env.ref("legal_department_management.action_report_ldm_engagement").report_action(self)

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_legal_task")
        action.update({"domain": [("engagement_id", "=", self.id)], "context": {"search_default_filter_open": 0}})
        return action

    def action_ldm_invoice(self):
        self.ensure_one()
        return self.env["legal.invoice.wizard"].ldm_open(engagement=self)

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------
    def _ldm_generate_retainer_lines(self, start=None):
        """A retainer bills a year ahead: twelve monthly lines, or one yearly line."""
        Line = self.env["legal.engagement.line"]
        for engagement in self.filtered(lambda e: e.fee_type == "retainer" and e.amount):
            first = start or engagement.retainer_next_date or engagement.date_start or fields.Date.context_today(engagement)
            if not start and engagement.line_ids:
                continue
            if engagement.retainer_period == "yearly":
                values = [{
                    "engagement_id": engagement.id, "sequence": 1, "trigger_event": "date", "date": first,
                    "name": _("Retainer from %(start)s to %(end)s", start=format_date(self.env, first),
                              end=format_date(self.env, first + relativedelta(years=1, days=-1))),
                    "amount": engagement.amount * 12,
                }]
            else:
                values = [{
                    "engagement_id": engagement.id, "sequence": month + 1, "trigger_event": "date",
                    "date": first + relativedelta(months=month),
                    "name": _("Retainer for %s", format_date(self.env, first + relativedelta(months=month),
                                                             date_format="MMMM y")),
                    "amount": engagement.amount,
                } for month in range(12)]
            Line.create(values)
            engagement.retainer_next_date = first + relativedelta(years=1)

    def _ldm_due_dated_lines(self):
        today = fields.Date.context_today(self)
        lines = self.line_ids.filtered(lambda l: l.state == "planned" and l.trigger_event == "date"
                                       and l.date and l.date <= today)
        lines._ldm_make_due()

    def _ldm_fire(self, event, tasks=None, amount=None, currency=None):
        """Make due the planned lines of ``event``: the lines of ``tasks`` and the
        lines that belong to no particular matter. Returns the lines made due."""
        due = self.env["legal.engagement.line"]
        for engagement in self.filtered(lambda e: e.state == "active"):
            lines = engagement.line_ids.filtered(
                lambda l: l.state == "planned" and l.trigger_event == event
                and (not tasks or not l.task_id or l.task_id in tasks))
            lines._ldm_make_due()
            due |= lines
            if event == "collection" and not lines and engagement.success_percent and amount:
                collected = (currency or engagement.currency_id)._convert(
                    amount, engagement.currency_id, engagement.company_id, fields.Date.context_today(self))
                due |= self.env["legal.engagement.line"].create({
                    "engagement_id": engagement.id, "task_id": tasks[:1].id if tasks else False,
                    "trigger_event": "collection", "date": fields.Date.context_today(self), "state": "due",
                    "name": _("Success fee: %(percent)s%% of %(amount)s collected",
                              percent=engagement.success_percent,
                              amount=money_text(self.env, [(engagement.currency_id, collected)])),
                    "amount": engagement.currency_id.round(collected * engagement.success_percent / 100.0),
                })
        return due

    def _ldm_add_due_line(self, name, task=None, amount=None):
        self.ensure_one()
        return self.env["legal.engagement.line"].create({
            "engagement_id": self.id, "task_id": task.id if task else False, "trigger_event": "manual",
            "date": fields.Date.context_today(self), "state": "due", "name": name,
            "amount": self.amount if amount is None else amount,
        })

    @api.model
    def _cron_ldm_fee_schedule(self):
        """Daily: dated instalments fall due, retainers renew for another year,
        and instalments whose invoice is paid are marked paid."""
        today = fields.Date.context_today(self)
        active = self.search([("state", "=", "active")])
        active._ldm_due_dated_lines()
        for engagement in active.filtered(lambda e: e.fee_type == "retainer" and e.retainer_next_date
                                          and e.retainer_next_date <= today
                                          and (not e.date_end or e.date_end > e.retainer_next_date)):
            engagement._ldm_generate_retainer_lines(start=engagement.retainer_next_date)
            engagement._ldm_due_dated_lines()
        invoiced = self.env["legal.engagement.line"].sudo().search([("state", "=", "invoiced")])
        invoiced.filtered(lambda l: l.invoice_line_id.move_id.payment_state in ("paid", "in_payment")).write(
            {"state": "paid"})
        return True


class LegalEngagementLine(models.Model):
    _inherit = "legal.engagement.line"

    legal_company_id = fields.Many2one(related="engagement_id.legal_company_id", store=True, string="Client")
    engagement_state = fields.Selection(related="engagement_id.state", string="Agreement status")
    invoice_id = fields.Many2one(related="invoice_line_id.move_id", string="Invoice",
                                 groups="account.group_account_invoice,account.group_account_readonly")
    payment_state = fields.Selection(related="invoice_line_id.move_id.payment_state", string="Payment",
                                     groups="account.group_account_invoice,account.group_account_readonly")
    waive_reason = fields.Char(string="Why it was waived", readonly=True, copy=False)
    is_overdue = fields.Boolean(string="Overdue", compute="_compute_is_overdue")

    @api.depends("state", "date")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for line in self:
            line.is_overdue = bool(line.state == "due" and line.date and line.date < today)

    def write(self, vals):
        if not self.env.su and {"amount", "engagement_id"} & set(vals) \
                and any(l.state in ("invoiced", "paid") for l in self):
            raise UserError(_("An invoiced instalment cannot change. Cancel its invoice first."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su and any(l.state in ("invoiced", "paid") for l in self):
            raise UserError(_("An invoiced instalment cannot be deleted. Cancel its invoice first."))
        return super().unlink()

    def _ldm_make_due(self):
        today = fields.Date.context_today(self)
        for line in self.filtered(lambda l: l.state == "planned"):
            line.write({"state": "due", "date": line.date or today})
            line.engagement_id.message_post(body=_("Now due: %(name)s, %(amount)s.", name=line.name,
                                                   amount=money_text(self.env, [(line.currency_id, line.amount)]) or "0"))

    def action_ldm_mark_due(self):
        self.filtered(lambda l: l.state == "planned")._ldm_make_due()
        return True

    def action_ldm_waive(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Waive instalments"),
            "res_model": "legal.fee.waive.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_line_ids": self.filtered(lambda l: l.state in ("planned", "due")).ids},
        }

    def _ldm_waive(self, reason):
        if not (reason or "").strip():
            raise UserError(_("Say why the instalments are waived."))
        lines = self.filtered(lambda l: l.state in ("planned", "due"))
        lines.write({"state": "waived", "waive_reason": reason})
        for engagement in lines.engagement_id:
            names = ", ".join(lines.filtered(lambda l: l.engagement_id == engagement).mapped("name"))
            engagement.message_post(body=_("Waived by %(user)s: %(lines)s. Reason: %(reason)s",
                                           user=self.env.user.name, lines=names, reason=reason))
        return True

    def action_ldm_remind(self):
        self.ensure_one()
        return self.env["legal.client.message.wizard"].ldm_open("instalment_due", fee_line=self)

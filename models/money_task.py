# -*- coding: utf-8 -*-
"""Money on the matter: billing state, the fee schedule's events, the
conflict check's hooks, and the chips the cockpit shows."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

from .ldm_reminders import ldm_day, ldm_key
from .money_conflict import _template_create, conflict_key, in_template_create
from .money_whatsapp import money_text

MONEY_READERS = "legal_department_management.group_ldm_clerk,legal_department_management.group_ldm_auditor"
OPEN = ("draft", "in_progress", "pending_docs")


class LegalTask(models.Model):
    _inherit = "legal.task"

    ldm_conflict_check_ids = fields.One2many("legal.conflict.check", "task_id", string="Conflict checks",
                                             groups=MONEY_READERS)
    ldm_conflict_state = fields.Selection(
        [("none", "Not checked"), ("pending", "Waiting for a decision"), ("clear", "No conflict"),
         ("override", "Accepted despite a match"), ("declined", "Declined")],
        string="Conflict check", compute="_compute_ldm_conflict", store=True, default="none")
    ldm_conflict_check_id = fields.Many2one("legal.conflict.check", string="Latest conflict check",
                                            compute="_compute_ldm_conflict", store=True, groups=MONEY_READERS)
    ldm_no_signed_agreement = fields.Boolean(string="No signed fee agreement", compute="_compute_ldm_agreement",
                                             search="_search_ldm_no_signed_agreement")
    ldm_fund_balance_text = fields.Char(string="Client money held", compute="_compute_ldm_money")
    ldm_invoice_count = fields.Integer(string="Number of invoices", compute="_compute_ldm_money")
    ldm_time_hours = fields.Float(string="Hours", compute="_compute_ldm_money")
    ldm_unbilled_text = fields.Char(string="To invoice", compute="_compute_ldm_money")
    ldm_can_message = fields.Boolean(compute="_compute_ldm_can_message")

    @api.model
    def _ldm_user_can_message(self):
        """Messages to clients: the switch is on and the user is on the legal or billing team."""
        user = self.env.user
        return bool(self._ldm_feature("group_ldm_client_messages") and (
            user.has_group("legal_department_management.group_ldm_clerk")
            or user.has_group("legal_department_management.group_ldm_billing_user")))

    @api.depends_context("uid")
    def _compute_ldm_can_message(self):
        allowed = self._ldm_user_can_message()
        for task in self:
            task.ldm_can_message = allowed

    @api.depends("ldm_conflict_check_ids.decision")
    def _compute_ldm_conflict(self):
        for task in self:
            checks = task.sudo().ldm_conflict_check_ids.sorted("id")
            decisions = set(checks.mapped("decision"))
            live = checks.filtered(lambda c: c.decision != "superseded")
            task.ldm_conflict_check_id = live[-1:] or checks[-1:]
            if "declined" in decisions:
                task.ldm_conflict_state = "declined"
            elif "pending" in decisions:
                task.ldm_conflict_state = "pending"
            elif live:
                task.ldm_conflict_state = live[-1].decision
            else:
                task.ldm_conflict_state = "none"

    @api.depends("engagement_id.signed", "state")
    def _compute_ldm_agreement(self):
        for task in self:
            task.ldm_no_signed_agreement = task.state not in ("draft", "cancelled") and not task.engagement_id.signed

    def _search_ldm_no_signed_agreement(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented
        missing = Domain("state", "not in", ("draft", "cancelled")) & ~Domain("engagement_id.signed", "=", True)
        return missing if (operator == "=") == value else ~missing

    def _compute_ldm_money(self):
        funds = self.env["legal.client.fund.line"].ldm_balance_text(self.legal_company_id)
        moves = self.env["account.move"].sudo()._read_group(
            [("ldm_task_ids", "in", self.ids), ("state", "!=", "cancel")], ["ldm_task_ids"], ["__count"])
        invoices = {task.id: count for task, count in moves}
        hours = {task.id: total for task, total in self.env["legal.time.entry"].sudo()._read_group(
            [("task_id", "in", self.ids)], ["task_id"], ["duration:sum"])}
        unbilled = {}
        for task, currency, total in self.env["legal.billable"].sudo()._read_group(
                [("task_id", "in", self.ids)], ["task_id", "currency_id"], ["amount:sum"]):
            unbilled.setdefault(task.id, []).append((currency, total))
        for task in self:
            task.ldm_fund_balance_text = funds.get(task.legal_company_id.id) or False
            task.ldm_invoice_count = invoices.get(task.id, 0)
            task.ldm_time_hours = hours.get(task.id, 0.0)
            task.ldm_unbilled_text = money_text(self.env, unbilled.get(task.id, [])) or False

    def _compute_billing_state(self):
        """Replaces the foundation's placeholder: "to invoice" while anything of
        the matter waits in To invoice, "invoiced" once it has invoices."""
        pending = {task.id for task, _count in self.env["legal.billable"].sudo()._read_group(
            [("task_id", "in", self.ids)], ["task_id"], ["__count"])}
        moves = self.env["account.move"].sudo().search([("ldm_task_ids", "in", self.ids), ("state", "!=", "cancel")])
        for task in self:
            invoices = moves.filtered(lambda m, t=task: t in m.ldm_task_ids)
            task.invoice_ids = invoices
            if task.id in pending:
                task.billing_state = "to_invoice"
            elif invoices:
                task.billing_state = "invoiced"
            else:
                task.billing_state = "none"

    @api.constrains("engagement_id", "legal_company_id")
    def _check_engagement_client(self):
        for task in self.filtered("engagement_id"):
            if task.engagement_id.legal_company_id != task.legal_company_id:
                raise ValidationError(_("The fee agreement of %s belongs to another client.", task.display_name))

    # ------------------------------------------------------------------
    # CRUD hooks
    # ------------------------------------------------------------------
    def write(self, vals):
        if in_template_create() and vals.get("state") in ("in_progress", "pending_docs"):
            held = self.filtered(lambda t: t.state == "draft" and t.ldm_conflict_state in ("pending", "declined"))
            if held:
                rest = dict(vals)
                rest.pop("state")
                result = super(LegalTask, held).write(rest) if rest else True
                others = self - held
                return super(LegalTask, others).write(vals) if others else result
        starting = closing = self.browse()
        if "state" in vals:
            starting = self.filtered(lambda t: t.state == "draft" and vals["state"] in ("in_progress", "pending_docs"))
            closing = self.filtered(lambda t: t.state != "done" and vals["state"] == "done")
        to_execution = self.filtered(lambda t: t.court_stage != "execution") \
            if vals.get("court_stage") == "execution" else self.browse()
        result = super().write(vals)
        if closing:
            closing._ldm_on_done()
        if starting:
            starting._ldm_on_start()
        if to_execution:
            to_execution._ldm_fire_fee_event("execution_opened")
        if {"legal_company_id", "counterparty_id"} & set(vals):
            self._ldm_rerun_conflict_check()
        if "engagement_id" in vals:
            self.filtered(lambda t: t.engagement_id.signed)._ldm_close_reminders("ldm_activity_fee_unsigned")
        return result

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        tasks.filtered("counterparty_id")._ldm_rerun_conflict_check()
        return tasks

    @api.model
    def create_from_template(self, vals):
        """Keep the foundation's contract; a matter whose conflict check is
        waiting for a manager is created and stays New instead of failing."""
        _template_create.depth = getattr(_template_create, "depth", 0) + 1
        try:
            return super().create_from_template(vals)
        finally:
            _template_create.depth -= 1

    def action_approve(self):
        _template_create.depth = getattr(_template_create, "depth", 0) + 1
        try:
            return super().action_approve()
        finally:
            _template_create.depth -= 1

    def _ldm_check_transition(self, new_state, trusted=False):
        super()._ldm_check_transition(new_state, trusted)
        if self.state == "draft" and new_state in ("in_progress", "pending_docs") and not self.env.su:
            if self.ldm_conflict_state == "pending":
                raise UserError(_("%s is waiting for a legal manager to decide on a possible conflict of interest.",
                                  self.display_name))
            if self.ldm_conflict_state == "declined":
                raise UserError(_("%s was declined after the conflict check and cannot start.", self.display_name))

    # ------------------------------------------------------------------
    # Fee schedule events
    # ------------------------------------------------------------------
    def _ldm_fire_fee_event(self, event, amount=None, currency=None):
        due = self.env["legal.engagement.line"]
        for task in self.filtered("engagement_id"):
            due |= task.engagement_id.sudo()._ldm_fire(event, tasks=task, amount=amount, currency=currency)
        return due

    def _ldm_on_done(self):
        for task in self:
            task._ldm_fire_fee_event("closing")
            engagement = task.engagement_id.sudo()
            if engagement.state == "active" and engagement.fee_type == "per_transaction" and engagement.amount:
                engagement._ldm_add_due_line(_("Transaction: %s", task.display_name), task)

    def _ldm_on_start(self):
        if not self._ldm_feature("group_ldm_billing"):
            return
        activity_type = self.env.ref("legal_department_management.ldm_activity_fee_unsigned",
                                     raise_if_not_found=False)
        for task in self.filtered(lambda t: t.company_id.ldm_engagement_required and t.ldm_no_signed_agreement):
            summary = _("Get the fee agreement signed — %s", task.task_number or task.name)
            user = task.lawyer_id or self.env.user
            if not task.activity_ids.filtered(lambda a, u=user: a.user_id == u and a.summary == summary):
                task.sudo().activity_schedule(activity_type_id=activity_type.id if activity_type else False,
                                              summary=summary, user_id=user.id,
                                              date_deadline=fields.Date.context_today(self))
            task.message_post(body=_("Work started without a signed fee agreement. Without a written agreement a "
                                     "fee claim lapses after three years (Advocacy Law Art. 65)."))

    # ------------------------------------------------------------------
    # Conflict check (cross-stream interface, SPEC 11)
    # ------------------------------------------------------------------
    @api.model
    def ldm_conflict_check(self, names, task_id=False, client_id=False):
        """Check ``names`` (the people or companies the matter is against) for
        the client ``client_id`` (or the client of ``task_id``).

        Returns ``{"hits": [...], "policy": "warn"|"block", "check_id": id,
        "decision": "pending"|"clear"|..., "conflict_count": n}``. Each hit is
        ``{"label", "role", "name", "conflict", "redacted", "responsible",
        "model", "id"}``, already redacted for the caller. The check is recorded;
        a check run without a matter is adopted by the matter the same user
        creates for the same names within 30 minutes."""
        policy = self.env.company.ldm_conflict_policy
        if not self._ldm_feature("group_ldm_conflicts"):
            return {"hits": [], "policy": policy, "check_id": False, "decision": "clear", "conflict_count": 0}
        task = self.browse(task_id).exists() if task_id else self.browse()
        client = self.env["legal.company"].browse(client_id).exists() if client_id else task.legal_company_id
        Check = self.env["legal.conflict.check"]
        check = Check._ldm_run(names, task=task, client=client)
        hits = Check._ldm_present(check.sudo().hits or [])
        return {"hits": hits, "policy": check.sudo().policy or policy, "check_id": check.id,
                "decision": check.sudo().decision, "conflict_count": check.sudo().hit_count}

    def _ldm_opposing_names(self):
        self.ensure_one()
        names = [p.partner_id.name for p in self.party_ids
                 if not p.is_client_side and p.role not in ("witness", "expert") and p.partner_id.name]
        if self.counterparty_id.name:
            names.append(self.counterparty_id.name)
        return list(dict.fromkeys(names))

    def _ldm_rerun_conflict_check(self):
        """Run the check again when the client or the other side changes."""
        if not self or not self._ldm_feature("group_ldm_conflicts"):
            return
        Check = self.env["legal.conflict.check"]
        for task in self:
            names = task._ldm_opposing_names()
            if not names:
                continue
            checks = task.sudo().ldm_conflict_check_ids.sorted("id")
            wanted = {conflict_key(n) for n in names}
            last = checks.filtered(lambda c: c.decision != "superseded")[-1:]
            if last and last.legal_company_id == task.legal_company_id:
                checked = {conflict_key(n) for n in (last.query or "").split(", ")}
                if wanted <= checked:
                    continue
            new = Check._ldm_run(names, task=task)
            Check._ldm_supersede(checks.filtered(lambda c: c.decision == "pending") - new, new)

    def action_ldm_open_conflict(self):
        self.ensure_one()
        check = self.sudo().ldm_conflict_check_id
        if not check:
            return False
        if check.decision == "pending" and self.env.user.has_group("legal_department_management.group_legal_manager"):
            return check.with_env(self.env).action_ldm_decide()
        return {"type": "ir.actions.act_window", "res_model": "legal.conflict.check", "res_id": check.id,
                "views": [[False, "form"]], "target": "new", "name": _("Conflict check")}

    def action_ldm_ask_conflict_decision(self):
        self.ensure_one()
        return self.sudo().ldm_conflict_check_id.with_env(self.env).action_ldm_send_to_partner()

    # ------------------------------------------------------------------
    # Reminders (extends the foundation's engine)
    # ------------------------------------------------------------------
    @api.model
    def _ldm_reminder_items(self, company, today, horizon):
        items = super()._ldm_reminder_items(company, today, horizon)
        if not self._ldm_feature("group_ldm_billing"):
            return items
        return items + self._ldm_instalment_items(company, today, horizon)

    @api.model
    def _ldm_instalment_items(self, company, today, horizon):
        """One reminder per agreement and matter: a single due instalment by its
        name, several as one line ("3 instalments due since 1 June"), so a
        retainer left unbilled for months is one row on My Day, not one a month."""
        lines = self.env["legal.engagement.line"].sudo().search([
            ("company_id", "=", company.id), ("state", "=", "due"), ("date", "<=", horizon),
            ("engagement_id.state", "=", "active")], order="date, id")
        groups = {}
        for line in lines:
            task = line.task_id or line.engagement_id.task_ids.filtered(lambda t: t.state in OPEN)[:1]
            if task:
                groups.setdefault((line.engagement_id, task), []).append(line)
        items = []
        for (engagement, task), group in groups.items():
            user = engagement.lawyer_id or task.lawyer_id
            env = self._ldm_reminder_env(user)
            first = group[0]
            if len(group) == 1:
                summary = env._("Instalment due %(date)s: %(name)s — %(number)s",
                                date=ldm_day(env, first.date, today), name=first.name, number=task.task_number)
                key = ldm_key(first)
            else:
                summary = env._("%(count)s instalments due since %(date)s: %(name)s — %(number)s",
                                count=len(group), date=ldm_day(env, first.date, today), name=engagement.name,
                                number=task.task_number)
                key = ldm_key(engagement, f"due-{task.id}")
            items.append((task, user, first.date, summary, "ldm_activity_fee_agreement", key))
        return items

    @api.model
    def _ldm_run_reminders(self):
        result = super()._ldm_run_reminders()
        self._ldm_sweep_instalment_reminders()
        return result

    @api.model
    def _ldm_sweep_instalment_reminders(self):
        """Close the instalment reminders that no longer name anything due: the
        instalments were invoiced, paid or waived, or several now share one
        reminder. Runs after the daily reminders and whenever an instalment's
        state changes."""
        activity_type = self.env.ref("legal_department_management.ldm_activity_fee_agreement",
                                     raise_if_not_found=False)
        if not activity_type:
            return
        Activity = self.env["mail.activity"].sudo()
        for company in self.env["res.company"].sudo().search([]):
            today, horizon = self._ldm_reminder_window(company)
            wanted = set()
            if self._ldm_feature("group_ldm_billing"):
                wanted = {item[5] for item in self.with_company(company)._ldm_instalment_items(company, today, horizon)}
            open_reminders = Activity.search([
                ("activity_type_id", "=", activity_type.id), ("res_model", "=", "legal.task"),
                ("ldm_reminder_key", "=like", "legal.engagement%")])
            tasks = self.sudo().browse(open_reminders.mapped("res_id")).filtered(lambda t: t.company_id == company)
            stale = open_reminders.filtered(lambda a: a.res_id in tasks.ids and a.ldm_reminder_key not in wanted)
            if stale:
                stale.action_feedback(feedback=_("No longer due: invoiced, paid or waived."))

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_ldm_client_money(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_client_fund")
        action.update({"domain": [("legal_company_id", "=", self.legal_company_id.id)],
                       "context": {"default_legal_company_id": self.legal_company_id.id,
                                   "default_task_id": self.id}})
        return action

    def action_ldm_receive_client_money(self):
        self.ensure_one()
        return self.env["legal.client.fund.line"].ldm_action_move("deposit", self.legal_company_id.id, self.id)

    def action_ldm_invoices(self):
        self.ensure_one()
        moves = self.env["account.move"].search([("ldm_task_ids", "in", self.id)])
        action = self.env["ir.actions.act_window"]._for_xml_id("account.action_move_out_invoice_type")
        action.update({"domain": [("id", "in", moves.ids)], "context": {"create": False}})
        if len(moves) == 1:
            action.update({"views": [[False, "form"]], "res_id": moves.id})
        return action

    def action_ldm_time(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("legal_department_management.action_ldm_time_entry")
        action.update({"domain": [("task_id", "=", self.id)], "context": {"default_task_id": self.id}})
        return action

    def action_ldm_invoice(self):
        return self.env["legal.invoice.wizard"].ldm_open(tasks=self)

    def action_ldm_message(self):
        self.ensure_one()
        code, hearing = self._ldm_message_suggestion()
        return self.env["legal.client.message.wizard"].ldm_open(code, task=self, hearing=hearing)

    def _ldm_message_suggestion(self):
        """The message a client most likely needs now: the result of a session
        held in the last three days, a reminder of the next session, or the
        documents still missing."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        held = self.hearing_ids.filtered(lambda h: h.state == "held" and h.date and (today - h.date).days <= 3)
        if held:
            return "hearing_result", held.sorted("date")[-1]
        planned = self.hearing_ids.filtered(lambda h: h.state == "planned" and h.date and h.date >= today)
        if planned:
            return "hearing_reminder", planned.sorted("date")[0]
        if self.missing_document_count:
            return "missing_documents", None
        return False, None


class LegalTaskParty(models.Model):
    _inherit = "legal.task.party"

    @api.model_create_multi
    def create(self, vals_list):
        parties = super().create(vals_list)
        parties.task_id._ldm_rerun_conflict_check()
        return parties

    def write(self, vals):
        result = super().write(vals)
        if {"partner_id", "is_client_side", "role"} & set(vals):
            self.task_id._ldm_rerun_conflict_check()
        return result


class LegalCourtStage(models.Model):
    _inherit = "legal.court.stage"

    @api.model_create_multi
    def create(self, vals_list):
        stages = super().create(vals_list)
        for stage in stages:
            task = stage.task_id
            if len(task.court_stage_ids) == 1:
                task._ldm_fire_fee_event("filing")
            if stage.stage == "execution":
                task._ldm_fire_fee_event("execution_opened")
        return stages


class LegalJudgment(models.Model):
    _inherit = "legal.judgment"

    @api.model_create_multi
    def create(self, vals_list):
        judgments = super().create(vals_list)
        for judgment in judgments:
            stage = judgment.court_stage or judgment.task_id.court_stage
            if stage in (False, "first_instance"):
                judgment.task_id._ldm_fire_fee_event("judgment_first_instance")
            if judgment.final_date:
                judgment.task_id._ldm_fire_fee_event("judgment_final")
        return judgments

    def write(self, vals):
        result = super().write(vals)
        if vals.get("final_date"):
            self.task_id._ldm_fire_fee_event("judgment_final")
        return result


class LegalHearing(models.Model):
    _inherit = "legal.hearing"

    def write(self, vals):
        held = self.filtered(lambda h: h.state != "held") if vals.get("state") == "held" else self.browse()
        result = super().write(vals)
        held._ldm_bill_per_hearing()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        hearings = super().create(vals_list)
        hearings.filtered(lambda h: h.state == "held")._ldm_bill_per_hearing()
        return hearings

    def _ldm_bill_per_hearing(self):
        for hearing in self:
            engagement = hearing.task_id.engagement_id.sudo()
            if engagement.state == "active" and engagement.fee_type == "per_hearing" and engagement.amount:
                engagement._ldm_add_due_line(
                    _("Court session of %s", fields.Date.to_string(hearing.date)), hearing.task_id)

    def action_ldm_client_message(self):
        """Interface for the litigation and workspace streams: offer the client
        message about this session (its result once held, else a reminder)."""
        self.ensure_one()
        code = "hearing_result" if self.state == "held" else "hearing_reminder"
        return self.env["legal.client.message.wizard"].ldm_open(code, task=self.task_id, hearing=self)

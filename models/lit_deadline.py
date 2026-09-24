# -*- coding: utf-8 -*-
"""The deadline engine: dates from the statutory periods, chains of periods,
lapse and escalation. Every date comes from res.company.ldm_statutory_dates on
the court's calendar; nothing here counts days by itself."""
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .lit_rules import ldm_date, ldm_user_is

OPEN = ("open", "awaiting_service")


class LegalDeadline(models.Model):
    _inherit = "legal.deadline"

    state = fields.Selection(
        selection_add=[("lapsed", "Ended unused")], ondelete={"lapsed": "set default"},
        help="Ended unused: a period that belonged to the other side or to an authority ended without "
        "anyone acting on it. Nothing was missed on our side.")
    our_action = fields.Boolean(
        string="We must act", default=True,
        help="Off for a period that runs for the other side (a judgment in our favour) or for an "
        "authority (the time it has to answer a grievance). Such a period ends unused, not missed.")
    date_done = fields.Date(string="Met on", readonly=True, copy=False)
    next_deadline_ids = fields.One2many("legal.deadline", "previous_deadline_id", string="Next periods")
    rule_basis = fields.Char(related="rule_id.basis", string="Legal basis")
    rule_verification = fields.Selection(related="rule_id.verification", string="Confidence")
    rule_peremptory = fields.Boolean(related="rule_id.peremptory", string="Cannot be extended")
    rule_source_url = fields.Char(related="rule_id.source_url", string="Source")
    rolled = fields.Boolean(string="Moved off a holiday", compute="_compute_rolled",
                            help="The period ends on a weekend or holiday, so the law gives until the next working day.")

    @api.depends("date_safe", "date_deadline")
    def _compute_rolled(self):
        for deadline in self:
            deadline.rolled = bool(deadline.date_safe and deadline.date_deadline
                                   and deadline.date_deadline != deadline.date_safe)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        Task = self.env["legal.task"]
        Rule = self.env["legal.appeal.rule"]
        for vals in vals_list:
            task = Task.browse(vals["task_id"]) if vals.get("task_id") else Task
            rule = Rule.browse(vals["rule_id"]) if vals.get("rule_id") else Rule
            if task:
                vals.setdefault("company_id", task.company_id.id)
                vals.setdefault("legal_company_id", task.legal_company_id.id)
                if not vals.get("user_id"):
                    vals["user_id"] = task.lawyer_id.id
            if rule:
                if not vals.get("name"):
                    vals["name"] = rule.name
                vals.setdefault("kind", rule._ldm_deadline_kind())
                vals.setdefault("our_action", not rule._ldm_waits_for_answer())
                if not vals.get("date_start") and not vals.get("date_safe"):
                    vals.setdefault("state", "awaiting_service")
        deadlines = super().create(vals_list)
        for deadline, vals in zip(deadlines, vals_list):
            if deadline.rule_id and not vals.get("date_safe"):
                deadline._ldm_recompute_dates()
            elif deadline.date_safe and not deadline.date_deadline:
                deadline.date_deadline = deadline._ldm_roll(deadline.date_safe)
        return deadlines

    def write(self, vals):
        today = fields.Date.context_today(self)
        met = self.browse()
        closing = self.browse()
        if "state" in vals:
            if vals["state"] == "done":
                met = self.filtered(lambda d: d.state in OPEN)
                vals = dict(vals)
                vals.setdefault("date_done", today)
            if vals["state"] not in OPEN:
                closing = self.filtered(lambda d: d.state in OPEN)
        result = super().write(vals)
        if {"rule_id", "date_start"} & set(vals) and "date_safe" not in vals:
            self.filtered(lambda d: d.rule_id and d.state in OPEN)._ldm_recompute_dates()
        elif "date_safe" in vals and "date_deadline" not in vals:
            for deadline in self:
                roll = deadline._ldm_roll(deadline.date_safe)
                if deadline.date_deadline != roll:
                    super(LegalDeadline, deadline).write({"date_deadline": roll})
        if closing:
            closing._ldm_close_reminders()
        for deadline in met:
            deadline._ldm_start_next(deadline.date_done or today)
        return result

    @api.onchange("rule_id", "date_start")
    def _onchange_rule_dates(self):
        if self.rule_id and not self.name:
            self.name = self.rule_id.name
        if self.rule_id:
            self.kind = self.rule_id._ldm_deadline_kind()
        if self.rule_id and self.date_start:
            company = self.company_id or self.task_id.company_id or self.env.company
            self.date_safe, self.date_deadline = self.rule_id._ldm_dates(company, self.date_start, self._ldm_calendar())

    @api.onchange("date_safe")
    def _onchange_date_safe(self):
        if self.date_safe and not self.rule_id:
            self.date_deadline = self.date_safe

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    def _ldm_calendar(self):
        """The calendar of the court that gave the judgment, else of the
        matter's body, else the company's legal calendar."""
        self.ensure_one()
        court = self.judgment_id.department_id or self.task_id.department_id
        if court:
            return court._ldm_calendar()
        return (self.company_id or self.env.company)._ldm_calendar()

    def _ldm_roll(self, day):
        """The legal last day for an "act by" day: moved off a holiday only when
        the period's rule allows it; periods without a rule never move."""
        self.ensure_one()
        if not day or not self.rule_id or not self.rule_id.extends_on_holiday:
            return day
        return (self.company_id or self.env.company).ldm_roll_forward(day, self._ldm_calendar())

    def _ldm_recompute_dates(self):
        """Recount open deadlines that follow a rule. A judgment's deadline
        counts from the judgment (notification or pronouncement); any other
        from its own start date. Returns the moves as
        (deadline, old act-by, new act-by, old last day, new last day)."""
        moves = []
        for deadline in self:
            rule = deadline.rule_id
            if not rule or deadline.state not in OPEN:
                continue
            company = deadline.company_id or deadline.task_id.company_id or self.env.company
            cap_from = None
            if deadline.judgment_id and deadline.source_model == "legal.judgment":
                event = rule._ldm_event_date(deadline.judgment_id)
                cap_from = deadline.judgment_id.date
            else:
                event = deadline.date_start
            if event:
                safe, legal = rule._ldm_dates(company, event, deadline._ldm_calendar(), cap_from)
                state = "open"
            else:
                safe = legal = False
                state = "awaiting_service"
            vals = {}
            if deadline.date_start != (event or False):
                vals["date_start"] = event or False
            if deadline.date_safe != safe:
                vals["date_safe"] = safe
            if deadline.date_deadline != legal:
                vals["date_deadline"] = legal
            if deadline.state != state:
                vals["state"] = state
            if vals:
                old = (deadline.date_safe, deadline.date_deadline)
                super(LegalDeadline, deadline).write(vals)
                if old != (safe, legal):
                    moves.append((deadline, old[0], safe, old[1], legal))
        return moves

    @api.model
    def _ldm_describe(self, deadline, date_safe=None, date_deadline=None):
        """One line saying when to act, in the reader's language."""
        env = deadline.env
        date_safe = deadline.date_safe if date_safe is None else date_safe
        date_deadline = deadline.date_deadline if date_deadline is None else date_deadline
        if not date_safe:
            return _("%s: waiting for the notification date", deadline.name)
        if date_deadline and date_deadline != date_safe:
            return _("%(name)s: act by %(safe)s (legal last day %(legal)s)", name=deadline.name,
                     safe=ldm_date(env, date_safe), legal=ldm_date(env, date_deadline))
        return _("%(name)s: act by %(safe)s", name=deadline.name, safe=ldm_date(env, date_safe))

    @api.model
    def _ldm_post_moves(self, moves, reason):
        """Tell each matter which of its deadlines moved and why, notifying the
        people responsible for them."""
        by_record = {}
        for deadline, old_safe, new_safe, _old_legal, new_legal in moves:
            record = deadline.task_id or deadline
            by_record.setdefault(record, []).append((deadline, old_safe, new_safe, new_legal))
        for record, rows in by_record.items():
            lines = []
            partners = self.env["res.partner"]
            for deadline, old_safe, new_safe, new_legal in rows:
                now = self._ldm_describe(deadline, new_safe, new_legal)
                if old_safe:
                    lines.append(_("%(now)s (was %(old)s)", now=now, old=ldm_date(self.env, old_safe)))
                else:
                    lines.append(now)
                owner = deadline.user_id or deadline.task_id.lawyer_id
                if owner and owner.active:
                    partners |= owner.partner_id
            body = Markup("<p>%s</p><ul>%s</ul>") % (
                reason, Markup("").join(Markup("<li>%s</li>") % line for line in lines))
            record.message_post(body=body, partner_ids=partners.ids, message_type="comment",
                                subtype_xmlid="mail.mt_note")

    # ------------------------------------------------------------------
    # Chains
    # ------------------------------------------------------------------
    def _ldm_start_next(self, start, silence=False):
        """Start the period that follows this one (``rule.next_rule_id``): from
        its last day when it ended without an answer (silence counts as a
        rejection), from ``start`` when it was met and the next period runs from
        that step, or waiting for the decision or notification date otherwise.
        Once per deadline."""
        self.ensure_one()
        rule = self.rule_id.next_rule_id
        if not rule or self.next_deadline_ids.filtered(lambda d: d.rule_id == rule):
            return self.browse()
        if silence and rule.start_event != "previous_deadline_end":
            return self.browse()
        date_start = start if (silence or rule._ldm_starts_on_our_step()) else False
        # The chain is the engine's doing: a clerk who marks a grievance lodged
        # may not create deadlines, but the period that follows must exist.
        next_deadline = self.sudo().create({
            "rule_id": rule.id,
            "name": rule.name,
            "task_id": self.task_id.id,
            "company_id": self.company_id.id,
            "legal_company_id": self.legal_company_id.id,
            "judgment_id": self.judgment_id.id,
            "user_id": self.user_id.id,
            "date_start": date_start,
            "state": "open" if date_start else "awaiting_service",
            "previous_deadline_id": self.id,
            "source_model": self._name,
            "source_id": self.id,
        })
        if silence:
            reason = _("%(prev)s ended without an answer, which counts as a rejection. Next period:",
                       prev=self.name)
        else:
            reason = _("%(prev)s was met on %(date)s. Next period:", prev=self.name,
                       date=ldm_date(self.env, start))
        next_deadline = next_deadline.with_env(self.env)
        self._ldm_post_moves([(next_deadline, False, next_deadline.date_safe, False, next_deadline.date_deadline)],
                             reason)
        return next_deadline

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _ldm_check_can_act(self):
        if not ldm_user_is(self.env, "group_ldm_clerk"):
            raise AccessError(_("Only the legal team can change a deadline."))
        self.check_access("write")

    def action_ldm_mark_met(self):
        self._ldm_check_can_act()
        todo = self.filtered(lambda d: d.state in OPEN)
        if not todo:
            raise UserError(_("Only an open deadline can be marked as met."))
        todo.write({"state": "done"})
        for deadline in todo:
            (deadline.task_id or deadline).message_post(
                body=_("Deadline met: %s", deadline.name), message_type="comment", subtype_xmlid="mail.mt_note")
        return True

    def action_ldm_cancel(self):
        if not ldm_user_is(self.env, "group_legal_user"):
            raise AccessError(_("Only a lawyer can cancel a deadline."))
        self.check_access("write")
        todo = self.filtered(lambda d: d.state in OPEN)
        todo.write({"state": "cancelled"})
        for deadline in todo:
            (deadline.task_id or deadline).message_post(
                body=_("Deadline cancelled: %s", deadline.name), message_type="comment", subtype_xmlid="mail.mt_note")
        return True

    def action_ldm_reopen(self):
        if not ldm_user_is(self.env, "group_legal_manager"):
            raise AccessError(_("Only a legal manager can reopen a closed deadline."))
        todo = self.filtered(lambda d: d.state in ("done", "missed", "cancelled", "lapsed"))
        todo.write({"state": "open", "date_done": False, "escalated": False})
        todo._ldm_recompute_dates()
        return True

    def _ldm_close_reminders(self):
        """Close the reminder activities the daily run opened for these deadlines."""
        activity_type = self.env.ref("legal_department_management.ldm_activity_deadline", raise_if_not_found=False)
        if not activity_type:
            return
        for deadline in self.filtered("task_id"):
            activities = deadline.task_id.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type and deadline.name and deadline.name in (a.summary or ""))
            if activities:
                activities.sudo().action_feedback(feedback=_("Closed with the deadline."))

    # ------------------------------------------------------------------
    # Daily run
    # ------------------------------------------------------------------
    @api.model
    def _cron_ldm_deadlines(self):
        """Close the periods whose legal last day has passed, start the periods
        that follow an unanswered one, tell the responsible and the managers
        once about each missed deadline, and mark judgments final."""
        for company in self.env["res.company"].search([]):
            calendar = company._ldm_calendar()
            tz = (calendar and calendar.tz) or "Asia/Baghdad"
            today = fields.Date.context_today(self.with_context(tz=tz))
            self.with_company(company)._ldm_lapse(company, today)
        return True

    @api.model
    def _ldm_lapse(self, company, today):
        lapsed = self.search([
            ("company_id", "=", company.id), ("state", "=", "open"),
            "|", ("date_deadline", "<", today), "&", ("date_deadline", "=", False), ("date_safe", "<", today),
        ])
        for deadline in lapsed:
            waiting = deadline.rule_id.next_rule_id.start_event == "previous_deadline_end"
            if deadline.our_action and not waiting:
                deadline.write({"state": "missed"})
            else:
                deadline.write({"state": "lapsed"})
                if waiting:
                    deadline._ldm_start_next(deadline.date_deadline or deadline.date_safe, silence=True)
        for deadline in self.search([("company_id", "=", company.id), ("state", "=", "missed"),
                                     ("escalated", "=", False)]):
            deadline._ldm_escalate(company)
        lapsed.judgment_id._ldm_update_final_date()
        return lapsed

    def _ldm_escalate(self, company):
        """One message, once, to the responsible and the legal managers."""
        self.ensure_one()
        managers = self.env["legal.task"]._ldm_managers(company)
        people = (self.user_id | self.task_id.lawyer_id | managers).filtered(lambda u: u.active and not u.share)
        last_day = self.date_deadline or self.date_safe
        body = _("Missed deadline: %(name)s. The legal last day was %(date)s.", name=self.name,
                 date=ldm_date(self.env, last_day) if last_day else "")
        (self.task_id or self).message_post(body=body, partner_ids=people.partner_id.ids,
                                            message_type="comment", subtype_xmlid="mail.mt_note")
        self.escalated = True

    # ------------------------------------------------------------------
    # Calendar view: shade weekends and holidays of the legal calendar
    # ------------------------------------------------------------------
    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        calendar = self.env.company._ldm_calendar()
        if not calendar or not date_to:
            return {}
        return calendar._get_unusual_days(fields.Datetime.to_datetime(date_from), fields.Datetime.to_datetime(date_to))

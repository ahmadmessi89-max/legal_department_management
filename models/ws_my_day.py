# -*- coding: utf-8 -*-
"""مكتبي / My Day (SPEC 5.1 and 14.4): what needs me, in focus bands.

One call, ``legal.task.get_my_day(scope)``, returns the whole screen. It runs
as the reading user, so every row it returns is a row that user may open, and
an auditor gets the same screen with no actions on it. Each source is searched
with a limit and each band is cut at fifty rows, so a busy office costs the
same as a quiet one.

A row is one thing to do: the next step of a matter, a court session, a
deadline, a matter waiting for an approver, an activity. It carries the reason
it is on the list, the date it bites and at most one action.
"""
from collections import OrderedDict
from datetime import timedelta

from odoo import _, api, fields, models

from .ws_common import (
    BAND_LIMIT, BANDS, CLOSED_STATES, G_APPROVER, G_CLERK, G_LAWYER, LEGAL_ACTIVITY_MODELS, OPEN_STATES,
    REMINDER_TYPES, band_of, client_word, iso, matter_line, open_matter, role_of,
)

KIND_ORDER = {"approval": 0, "notification": 1, "hearing": 2, "visit": 3, "step": 4, "deadline": 5,
              "activity": 6, "target": 7, "waiting": 8, "idle": 9}


class LegalTask(models.Model):
    _inherit = "legal.task"

    @api.model
    def get_my_day(self, scope="me"):
        user = self.env.user
        today = fields.Date.context_today(self)
        role, role_label = role_of(self, user)
        is_manager = role == "manager"
        read_only = not user.has_group(G_CLERK)
        if read_only:
            scope = "all"
        elif scope not in ("me", "team", "all") or (scope != "me" and not is_manager):
            scope = "me"
        ctx = {
            "today": today,
            "scope": scope,
            "read_only": read_only,
            "is_lawyer": user.has_group(G_LAWYER) and not read_only,
            "is_manager": is_manager,
        }
        rows = []
        rows += self._ldm_md_step_rows(ctx)
        rows += self._ldm_md_hearing_rows(ctx)
        rows += self._ldm_md_deadline_rows(ctx)
        rows += self._ldm_md_target_rows(ctx, rows)
        rows += self._ldm_md_approval_rows(ctx)
        if not is_manager:
            rows += self._ldm_md_notification_rows(ctx)
        rows += self._ldm_md_activity_rows(ctx)
        bands = self._ldm_md_bands(rows, today)
        approvals = self._ldm_md_approval_chip(ctx)
        manager = self._ldm_md_manager_bands(ctx) if is_manager else []
        empty = not any(band["count"] for band in bands)
        return {
            "header": {
                "title": _("My Day"),
                "today": iso(today),
                "role": role,
                "role_label": role_label,
                "client_word": client_word(self, user),
                "user": user.name,
            },
            "scope": scope,
            "scopes": [
                {"key": "me", "label": _("Me")},
                {"key": "team", "label": _("My team")},
                {"key": "all", "label": _("Everyone")},
            ] if is_manager else [],
            "read_only": read_only,
            "can_create": not read_only,
            "bands": bands,
            "total": sum(band["count"] for band in bands),
            "agenda": self._ldm_md_agenda(ctx),
            "by_body": self._ldm_md_by_body(ctx) if not read_only else [],
            "advance": self._ldm_md_advance(ctx) if not read_only else [],
            "approvals": approvals,
            "manager": manager,
            "counts": self._ldm_md_counts(ctx) if (is_manager or read_only) else [],
            "all_clear": {
                "title": _("Nothing needs you today."),
                "hint": _("Open a new matter with New, or look through the matters register."),
            } if empty and not any(b["rows"] for b in manager) else False,
        }

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------
    def _ldm_md_scope_domain(self, ctx, user_field, task_path="task_id"):
        """Whose items: mine (assigned to me, or unassigned on a matter I am
        responsible for), my team's (matters I am on the team of), or all."""
        uid = self.env.uid
        if ctx["scope"] == "all":
            return []
        if ctx["scope"] == "team":
            return [(f"{task_path}.lawyer_ids", "in", [uid])]
        return ["|", (user_field, "=", uid), "&", (user_field, "=", False), (f"{task_path}.lawyer_id", "=", uid)]

    def _ldm_md_row(self, task, kind, day, reason, action=False, who="", key=None, extra=None):
        row = {
            "key": key or f"{kind}-{task.id}",
            "kind": kind,
            "date": iso(day),
            "subject": task.name,
            "number": task.task_number or "",
            "line": matter_line(task),
            "reason": reason or "",
            "urgent": task.is_urgent,
            "confidential": task.confidential,
            "who": who or "",
            "task_id": task.id,
            "open": open_matter(task),
            "action": action,
        }
        if extra:
            row.update(extra)
        return row

    def _ldm_md_step_rows(self, ctx):
        """The next open step of each matter (later steps depend on it)."""
        # Work does not start on a matter that waits for its approver.
        domain = [("state", "=", "todo"), ("task_id.state", "in", OPEN_STATES), ("task_id.active", "=", True),
                  ("task_id.approval_state", "!=", "to_approve")]
        domain += self._ldm_md_scope_domain(ctx, "user_id")
        steps = self.env["legal.task.step"].search(domain, limit=300)
        steps = steps.sorted(lambda s: (not s.date_due, s.date_due or fields.Date.today(), s.sequence, s.id))
        rows, seen = [], set()
        for step in steps:
            if step.task_id.id in seen:
                continue
            seen.add(step.task_id.id)
            task = step.task_id
            if step.is_visit:
                body = step.department_id.name or task.department_id.name
                reason = _("Visit %(body)s: %(step)s", body=body, step=step.name) if body else step.name
                action = {"type": "visit", "id": step.id, "label": _("Log visit")}
            else:
                reason = step.name
                action = {"type": "tick", "id": step.id, "label": _("Done")}
            rows.append(self._ldm_md_row(
                task, "visit" if step.is_visit else "step", step.date_due, reason,
                action=False if ctx["read_only"] else action,
                who=step.user_id.name or task.lawyer_id.name, key=f"step-{step.id}"))
        return rows

    def _ldm_md_hearing_rows(self, ctx):
        domain = [("state", "=", "planned"), ("task_id.state", "in", OPEN_STATES), ("task_id.active", "=", True)]
        domain += self._ldm_md_scope_domain(ctx, "attending_user_id")
        rows = []
        for hearing in self.env["legal.hearing"].search(domain, order="date, time", limit=100):
            task = hearing.task_id
            court = hearing.department_id.name or task.department_id.name
            if hearing.date < ctx["today"]:
                reason = _("Record what happened at the session")
            elif court:
                reason = _("Court session at %s", court)
            else:
                reason = _("Court session")
            action = {"type": "outcome", "id": hearing.id, "label": _("Record outcome")} if ctx["is_lawyer"] else False
            rows.append(self._ldm_md_row(
                task, "hearing", hearing.date, reason, action=action,
                who=hearing.attending_user_id.name or task.lawyer_id.name, key=f"hearing-{hearing.id}",
                extra={"time": hearing.time or 0.0}))
        return rows

    def _ldm_md_deadline_rows(self, ctx):
        domain = [("state", "=", "open"), ("date_safe", "!=", False)]
        uid = self.env.uid
        if ctx["scope"] == "me":
            domain += ["|", ("user_id", "=", uid), "&", ("user_id", "=", False), ("task_id.lawyer_id", "=", uid)]
        elif ctx["scope"] == "team":
            domain += [("task_id.lawyer_ids", "in", [uid])]
        rows = []
        for deadline in self.env["legal.deadline"].search(domain, order="date_safe", limit=100):
            task = deadline.task_id
            if task and (task.state in CLOSED_STATES or not task.active):
                continue
            if task:
                rows.append(self._ldm_md_row(task, "deadline", deadline.date_safe, deadline.name,
                                             who=deadline.user_id.name or task.lawyer_id.name,
                                             key=f"deadline-{deadline.id}"))
            else:
                rows.append({
                    "key": f"deadline-{deadline.id}", "kind": "deadline", "date": iso(deadline.date_safe),
                    "subject": deadline.legal_company_id.name or deadline.name, "number": "",
                    "line": "", "reason": deadline.name, "urgent": False, "confidential": False,
                    "who": deadline.user_id.name or "", "task_id": False,
                    "open": {"res_model": "legal.deadline", "res_id": deadline.id}, "action": False,
                })
        return rows

    def _ldm_md_target_rows(self, ctx, rows):
        """Matters that have nothing else on the list: their target date, or,
        without one, a reminder that nothing is planned."""
        listed = {row["task_id"] for row in rows if row.get("task_id")}
        uid = self.env.uid
        domain = [("state", "in", OPEN_STATES)]
        if ctx["scope"] == "me":
            domain += [("lawyer_id", "=", uid)]
        elif ctx["scope"] == "team":
            domain += [("lawyer_ids", "in", [uid])]
        out = []
        for task in self.search(domain + [("id", "not in", list(listed))], limit=100):
            if task.approval_state == "to_approve":
                out.append(self._ldm_md_row(task, "waiting", False, _("Waiting for an approver's decision"),
                                            who=task.lawyer_id.name))
            elif task.due_date:
                out.append(self._ldm_md_row(task, "target", task.due_date, _("Target date"),
                                            who=task.lawyer_id.name))
            else:
                out.append(self._ldm_md_row(task, "idle", False, _("Nothing planned: add the next step"),
                                            who=task.lawyer_id.name))
        return out

    def _ldm_md_can_approve(self):
        return self.env.user.has_group(G_APPROVER) and self._ldm_feature("group_ldm_approvals")

    def _ldm_md_approval_rows(self, ctx):
        if ctx["read_only"] or not self._ldm_md_can_approve():
            return []
        rows = []
        today = ctx["today"]
        for task in self.search([("approval_state", "=", "to_approve")], order="id", limit=50):
            if not task.ldm_can_decide:
                continue
            reason = _("Sent for approval by %s", task.approval_requested_by_id.name) \
                if task.approval_requested_by_id else _("Waiting for your approval")
            rows.append(self._ldm_md_row(task, "approval", today, reason,
                                         action={"type": "approve", "id": task.id, "label": _("Approve")},
                                         who=task.lawyer_id.name, key=f"approval-{task.id}",
                                         extra={"since": iso(task.ldm_waiting_since)}))
        return rows

    def _ldm_md_approval_chip(self, ctx):
        if ctx["read_only"] or not self._ldm_md_can_approve():
            return False
        tasks = self.search([("approval_state", "=", "to_approve")], limit=200)
        count = len(tasks.filtered("ldm_can_decide"))
        return {"count": count, "label": _("Awaiting my approval")}

    def _ldm_md_notification_rows(self, ctx, everyone=False):
        """Judgments whose challenge periods wait for the notification date
        (SPEC 14.1): one row per judgment, with the date typed in place."""
        if ctx["read_only"] or not ctx["is_lawyer"]:
            return []
        domain = [("state", "=", "awaiting_service"), ("judgment_id", "!=", False)]
        if not everyone:
            domain += [("task_id.lawyer_id", "=", self.env.uid)]
        judgments = self.env["legal.deadline"].search(domain, limit=100).judgment_id
        rows = []
        for judgment in judgments[:BAND_LIMIT]:
            task = judgment.task_id
            if task.state in CLOSED_STATES:
                continue
            rows.append(self._ldm_md_row(
                task, "notification", ctx["today"], _("Judgment given: when was it notified?"),
                action={"type": "notified", "id": judgment.id, "label": _("Save the date")},
                who=task.lawyer_id.name, key=f"notification-{judgment.id}",
                extra={"judgment_date": iso(judgment.date)}))
        return rows

    def _ldm_md_activity_rows(self, ctx):
        """My own activities on legal records, except the reminders of the
        items listed above."""
        excluded = [self.env.ref(f"legal_department_management.{x}", raise_if_not_found=False) for x in REMINDER_TYPES]
        excluded_ids = [t.id for t in excluded if t]
        Activity = self.env["mail.activity"]
        domain = [("user_id", "=", self.env.uid), ("res_model", "in", LEGAL_ACTIVITY_MODELS)]
        if excluded_ids:
            domain += [("activity_type_id", "not in", excluded_ids)]
        rows = []
        for activity in Activity.search(domain, order="date_deadline", limit=100):
            reason = activity.summary or activity.activity_type_id.name or ""
            if activity.res_model == "legal.task":
                task = self.browse(activity.res_id).exists()
                if not task or task.state in CLOSED_STATES:
                    continue
                row = self._ldm_md_row(task, "activity", activity.date_deadline, reason,
                                       key=f"activity-{activity.id}")
            else:
                row = {
                    "key": f"activity-{activity.id}", "kind": "activity", "date": iso(activity.date_deadline),
                    "subject": activity.res_name or "", "number": "", "line": "", "reason": reason,
                    "urgent": False, "confidential": False, "who": "", "task_id": False,
                    "open": {"res_model": activity.res_model, "res_id": activity.res_id},
                }
            row["action"] = False if ctx["read_only"] else {"type": "activity", "id": activity.id,
                                                              "label": _("Done")}
            rows.append(row)
        return rows

    # ------------------------------------------------------------------
    # Bands
    # ------------------------------------------------------------------
    def _ldm_md_bands(self, rows, today):
        titles = {
            "overdue": _("Overdue"),
            "today": _("Today"),
            "week": _("This week"),
            "later": _("Later"),
            "nodate": _("No date"),
        }
        grouped = OrderedDict((key, []) for key in BANDS)
        for row in rows:
            day = fields.Date.to_date(row["date"]) if row["date"] else False
            grouped[band_of(day, today)].append(row)
        bands = []
        for key, items in grouped.items():
            items.sort(key=lambda r: (
                r["date"] or "9999", not r["urgent"], KIND_ORDER.get(r["kind"], 9), r["subject"] or ""))
            if key in ("today", "nodate"):
                items.sort(key=lambda r: (not r["urgent"], KIND_ORDER.get(r["kind"], 9), r["subject"] or ""))
            bands.append({
                "key": key,
                "title": titles[key],
                "count": len(items),
                "rows": items[:BAND_LIMIT],
                "truncated": len(items) > BAND_LIMIT,
                "folded": key in ("later", "nodate"),
            })
        return bands

    # ------------------------------------------------------------------
    # Side panels
    # ------------------------------------------------------------------
    def _ldm_md_agenda(self, ctx):
        today = ctx["today"]
        end = today + timedelta(days=6)
        items = self._ldm_agenda_items(today, end, "me" if ctx["scope"] == "me" else "all", limit=60)
        days = OrderedDict()
        for offset in range(7):
            days[iso(today + timedelta(days=offset))] = []
        for item in items:
            days.setdefault(item["date"], []).append(item)
        return {
            "title": _("The next seven days"),
            "days": [{"date": day, "items": sorted(rows, key=lambda r: (r["order"], r["time"] or 99))}
                     for day, rows in days.items() if rows],
            "empty": _("Nothing is booked for the next seven days."),
        }

    def _ldm_md_by_body(self, ctx):
        """The runner's route: today's (and late) counter visits grouped by
        body, with the documents to carry for each matter."""
        uid = self.env.uid
        domain = [("state", "=", "todo"), ("is_visit", "=", True), ("date_due", "<=", ctx["today"]),
                  ("task_id.state", "in", OPEN_STATES),
                  "|", ("user_id", "=", uid), "&", ("user_id", "=", False), ("task_id.lawyer_id", "=", uid)]
        steps = self.env["legal.task.step"].search(domain, order="date_due, sequence", limit=60)
        doc_states = dict(self.env["legal.task.document"]._fields["state"]._description_selection(self.env))
        groups = OrderedDict()
        for step in steps:
            body = step.department_id or step.task_id.department_id
            key = body.id or 0
            if key not in groups:
                groups[key] = {
                    "key": f"body-{key}",
                    "body": body.name or _("No body set"),
                    "address": (body.address or "").strip().split("\n")[0] if body else "",
                    "hours": body.working_hours or "" if body else "",
                    "visits": [],
                }
            task = step.task_id
            docs = task.document_ids.filtered(lambda d: d.state != "not_needed")
            groups[key]["visits"].append({
                "step_id": step.id,
                "task_id": task.id,
                "number": task.task_number or "",
                "subject": task.name,
                "client": task.legal_company_id.name or "",
                "step": step.name,
                "date": iso(step.date_due),
                "documents": [{
                    "name": doc.name,
                    "state": doc.state,
                    "state_label": doc_states.get(doc.state, ""),
                    "have": doc.state in ("received", "verified"),
                } for doc in docs],
            })
        return list(groups.values())

    def _ldm_md_advance(self, ctx):
        """Cash a runner holds from an advance and has not accounted for yet."""
        advances = self.env["legal.advance"].search([("user_id", "=", self.env.uid), ("state", "=", "paid")])
        totals = OrderedDict()
        for advance in advances:
            totals.setdefault(advance.currency_id.id, 0.0)
            totals[advance.currency_id.id] += advance.balance
        label = _("Advance still to account for")
        return [{"amount": amount, "currency_id": currency_id, "label": label}
                for currency_id, amount in totals.items() if amount]

    def _ldm_md_manager_bands(self, ctx):
        today = ctx["today"]
        bands = []
        # Tomorrow's sessions nobody is attending.
        tomorrow = today + timedelta(days=1)
        hearings = self.env["legal.hearing"].search([
            ("state", "=", "planned"), ("attending_user_id", "=", False),
            ("date", ">=", tomorrow), ("date", "<=", tomorrow + timedelta(days=2)),
            ("task_id.state", "in", OPEN_STATES)], order="date, time", limit=BAND_LIMIT)
        rows = []
        for hearing in hearings:
            court = hearing.department_id.name or hearing.task_id.department_id.name
            reason = _("Court session at %s", court) if court else _("Court session")
            rows.append(self._ldm_md_row(hearing.task_id, "hearing", hearing.date, reason,
                                         key=f"unstaffed-{hearing.id}", extra={"time": hearing.time or 0.0}))
        bands.append({"key": "unstaffed", "title": _("Sessions in the next days with nobody attending"),
                      "rows": rows})
        # At the body past target (the government stream supplies the domain).
        if hasattr(self, "_ldm_past_target_domain"):
            tasks = self.search(self._ldm_past_target_domain(), limit=BAND_LIMIT)
            rows = []
            for task in tasks:
                reason = _("With the body for %s working days", task.days_at_body)
                rows.append(self._ldm_md_row(task, "target", task.date_submitted, reason, key=f"past-{task.id}"))
            bands.append({"key": "past_target", "title": _("At the body past the usual answer time"), "rows": rows})
        # Conflict checks waiting for a partner.
        Check = self.env["legal.conflict.check"]
        if Check.has_access("read"):
            checks = Check.search([("decision", "=", "pending")], limit=BAND_LIMIT)
            rows = []
            for check in checks:
                if check.task_id:
                    row = self._ldm_md_row(check.task_id, "conflict", False,
                                           _("Conflict check waiting for your decision"), key=f"conflict-{check.id}")
                else:
                    row = {"key": f"conflict-{check.id}", "kind": "conflict", "date": False,
                           "subject": check.query, "number": "", "line": "", "urgent": False,
                           "confidential": False, "who": check.user_id.name or "", "task_id": False,
                           "reason": _("Conflict check waiting for your decision"), "action": False}
                row["open"] = {"res_model": "legal.conflict.check", "res_id": check.id}
                rows.append(row)
            bands.append({"key": "conflicts", "title": _("Conflicts waiting for a decision"), "rows": rows})
        # Judgments waiting for their notification date.
        manager_ctx = dict(ctx, is_lawyer=True)
        bands.append({"key": "notifications", "title": _("Judgments waiting for their notification date"),
                      "rows": self._ldm_md_notification_rows(manager_ctx, everyone=True)})
        return [band for band in bands if band["rows"]]

    def _ldm_md_counts(self, ctx):
        """The oversight line: a handful of counts, each opening its records."""
        today = ctx["today"]
        week_end = today + timedelta(days=6)
        open_domain = [("state", "in", OPEN_STATES)]
        overdue = soon = 0
        for day, count in self._read_group(open_domain + [("next_date", "!=", False)], ["next_date:day"], ["__count"]):
            day = fields.Date.to_date(day)
            if day < today:
                overdue += count
            elif day <= week_end:
                soon += count
        total = self._read_group(open_domain, [], ["__count"])[0][0]
        counts = [
            {"key": "open", "label": _("Open matters"), "count": total, "tone": "neutral",
             "model": "legal.task", "domain": open_domain},
            {"key": "overdue", "label": _("Overdue"), "count": overdue, "tone": "danger",
             "model": "legal.task", "domain": open_domain + [("next_date", "<", iso(today))]},
            {"key": "week", "label": _("Due this week"), "count": soon, "tone": "warning",
             "model": "legal.task",
             "domain": open_domain + [("next_date", ">=", iso(today)), ("next_date", "<=", iso(week_end))]},
        ]
        if self._ldm_feature("group_ldm_approvals"):
            waiting = self._read_group([("approval_state", "=", "to_approve")], [], ["__count"])[0][0]
            counts.append({"key": "approval", "label": _("Awaiting approval"), "count": waiting, "tone": "info",
                           "model": "legal.task", "domain": [("approval_state", "=", "to_approve")]})
        sessions_domain = [("state", "=", "planned"), ("date", ">=", iso(today)), ("date", "<=", iso(week_end))]
        sessions = self.env["legal.hearing"]._read_group(sessions_domain, [], ["__count"])[0][0]
        counts.append({"key": "sessions", "label": _("Sessions this week"), "count": sessions, "tone": "neutral",
                       "model": "legal.hearing", "domain": sessions_domain})
        return counts

    # ------------------------------------------------------------------
    # Inline actions that are not a step tick
    # ------------------------------------------------------------------
    @api.model
    def ldm_my_day_activity_done(self, activity_id):
        activity = self.env["mail.activity"].browse(activity_id).exists()
        if not activity or activity.user_id != self.env.user:
            return False
        activity.action_feedback(feedback=_("Done from My Day"))
        return True

    @api.model
    def ldm_my_day_notified(self, judgment_id, notified_date):
        judgment = self.env["legal.judgment"].browse(judgment_id).exists()
        if not judgment:
            return False
        judgment.check_access("write")
        judgment.ldm_set_notified_date(fields.Date.to_date(notified_date))
        return True

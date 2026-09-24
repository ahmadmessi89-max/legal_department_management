# -*- coding: utf-8 -*-
"""The matter as the workspace sees it: the cockpit payload, the approvals
inbox preview, the agenda, and the few hooks the quick-create dialog needs."""
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .base_litigation import COURT_STAGES
from .ws_common import CLOSED_STATES, OPEN_STATES, iso, matter_line, open_matter

PHASE_ORDER = [key for key, _label in COURT_STAGES]


class LegalTask(models.Model):
    _inherit = "legal.task"

    ldm_approval_requested_date = fields.Datetime(
        string="Sent for approval on", readonly=True, copy=False,
        help="When the matter was last sent for approval.")
    ldm_waiting_since = fields.Date(string="Waiting since", compute="_compute_ldm_waiting_since")
    ldm_cockpit = fields.Json(string="Cockpit", compute="_compute_ldm_cockpit")

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    def write(self, vals):
        # The quick-create dialog opens a matter whose conflict check is waiting
        # for a partner: it must stay New, so the start that create_from_template
        # performs is skipped for that one call.
        if self.env.context.get("ldm_hold_draft") and vals.get("state") in ("in_progress", "pending_docs") \
                and all(task.state == "draft" for task in self):
            vals = {k: v for k, v in vals.items() if k != "state"}
            if not vals:
                return True
        return super().write(vals)

    def action_request_approval(self):
        result = super().action_request_approval()
        self.write({"ldm_approval_requested_date": fields.Datetime.now()})
        return result

    @api.depends_context("tz")
    @api.depends("ldm_approval_requested_date", "write_date")
    def _compute_ldm_waiting_since(self):
        for task in self:
            moment = task.ldm_approval_requested_date or task.write_date
            task.ldm_waiting_since = fields.Datetime.context_timestamp(task, moment).date() if moment else False

    # ------------------------------------------------------------------
    # Cockpit (SPEC 5.3, 14.4): one payload for the vitals strip, the next
    # step card, the approval banner and the phase rail.
    # ------------------------------------------------------------------
    @api.depends_context("uid", "lang", "tz")
    @api.depends("state", "approval_state", "next_date", "court_stage", "date_state_changed", "expenses_amount",
                 "step_ids.state", "step_ids.date_due", "hearing_ids.state", "hearing_ids.date",
                 "deadline_ids.state", "deadline_ids.date_safe", "document_ids.state", "court_stage_ids.stage")
    def _compute_ldm_cockpit(self):
        today = fields.Date.context_today(self)
        approvals_on = self._ldm_feature("group_ldm_approvals")
        for task in self:
            if not task.id:
                task.ldm_cockpit = {}
                continue
            can_write = task.has_access("write")
            approval = task._ldm_cockpit_approval() if approvals_on else False
            task.ldm_cockpit = {
                "kind": task.kind,
                "state": task.state,
                "read_only": not can_write,
                "closed": task.state in CLOSED_STATES,
                "vitals": task._ldm_cockpit_vitals(today),
                "next": False if approval and approval["state"] == "to_approve" else task._ldm_cockpit_next(today, can_write),
                "approval": approval,
                "phases": task._ldm_cockpit_phases() if task.kind == "litigation" else [],
            }

    def _ldm_cockpit_vitals(self, today):
        self.ensure_one()
        vitals = [{
            "key": "next",
            "label": _("Next date"),
            "date": iso(self.next_date),
            "days": (self.next_date - today).days if self.next_date else None,
            "hint": self.next_action or "",
            "tab": False,
        }]
        if self.kind in ("litigation", "execution"):
            hearings = self.hearing_ids.filtered(lambda h: h.state != "cancelled")
            held = hearings.filtered(lambda h: h.state == "held")
            vitals.append({"key": "sessions", "label": _("Sessions"),
                           "value": _("%(held)s held of %(total)s", held=len(held), total=len(hearings)),
                           "tab": "sessions"})
        docs = self.document_ids.filtered(lambda d: d.state != "not_needed")
        if docs:
            have = docs.filtered(lambda d: d.state in ("received", "verified"))
            expired = docs.filtered(lambda d: d.state == "expired")
            tone = "danger" if expired else ("warning" if len(have) < len(docs) else "success")
            vitals.append({"key": "documents", "label": _("Documents"),
                           "value": _("%(have)s of %(total)s", have=len(have), total=len(docs)),
                           "tone": tone, "tab": "documents"})
        steps = self.step_ids.filtered(lambda s: s.state != "skipped")
        if steps and self.kind != "litigation":
            done = steps.filtered(lambda s: s.state == "done")
            vitals.append({"key": "steps", "label": _("Steps"),
                           "value": _("%(done)s of %(total)s done", done=len(done), total=len(steps)),
                           "tab": "steps"})
        vitals.append({"key": "expenses", "label": _("Expenses"), "amount": self.expenses_amount,
                       "currency_id": self.company_currency_id.id, "tab": "money"})
        if self.date_state_changed and self.state not in CLOSED_STATES:
            since = fields.Datetime.context_timestamp(self, self.date_state_changed).date()
            state_label = dict(self._fields["state"]._description_selection(self.env)).get(self.state)
            vitals.append({"key": "age", "label": _("In this status"), "days": max(0, (today - since).days),
                           "hint": state_label, "tab": False})
        return vitals

    def _ldm_cockpit_approval(self):
        self.ensure_one()
        if self.approval_state not in ("to_approve", "rejected"):
            return False
        labels = dict(self._fields["approval_state"]._description_selection(self.env))
        return {
            "state": self.approval_state,
            "state_label": labels.get(self.approval_state),
            "requested_by": self.approval_requested_by_id.name or "",
            "since": iso(self.ldm_waiting_since),
            "decided_by": self.approver_id.name or "",
            "note": self.approval_note or "",
            "can_decide": self.ldm_can_decide,
            "can_request": self.ldm_can_request_approval,
        }

    def _ldm_cockpit_next(self, today, can_write):
        """The next open item and its one action (the card under the title)."""
        self.ensure_one()
        if self.state in CLOSED_STATES:
            labels = dict(self._fields["outcome"]._description_selection(self.env))
            return {"kind": "closed", "label": labels.get(self.outcome) or "", "date": iso(self.date_closed)}
        candidates = []
        for hearing in self.hearing_ids.filtered(lambda h: h.state == "planned" and h.date):
            candidates.append((hearing.date, 0, hearing))
        for deadline in self.deadline_ids.filtered(lambda d: d.state == "open" and d.date_safe):
            candidates.append((deadline.date_safe, 1, deadline))
        open_steps = self.step_ids.filtered(lambda s: s.state == "todo")
        for step in open_steps.filtered("date_due"):
            candidates.append((step.date_due, 2, step))
        if self.due_date:
            candidates.append((self.due_date, 3, self))
        if candidates:
            day, _order, item = min(candidates, key=lambda c: (c[0], c[1], c[2].id))
        elif open_steps:
            day, item = False, open_steps[0]
        elif self.state == "draft":
            return {"kind": "start", "label": _("Not started yet."), "date": False}
        else:
            return {"kind": "none", "label": _("Nothing is planned. Add a step or a court session."), "date": False}
        base = {"date": iso(day), "days": (day - today).days if day else None}
        if item._name == "legal.hearing":
            where = item.department_id.name or self.department_id.name or ""
            return dict(base, kind="hearing", id=item.id,
                        label=_("Court session at %s", where) if where else _("Court session"),
                        who=item.attending_user_id.name or "", time=item.time or 0.0,
                        can_act=bool(can_write and item.has_access("write")))
        if item._name == "legal.deadline":
            return dict(base, kind="deadline", id=item.id, label=item.name,
                        legal_date=iso(item.date_deadline), who=item.user_id.name or "",
                        can_act=False)
        if item._name == "legal.task.step":
            body = item.department_id.name if item.is_visit else ""
            return dict(base, kind="visit" if item.is_visit else "step", id=item.id, label=item.name,
                        body=body or "", who=item.user_id.name or "",
                        can_act=bool(can_write and item.has_access("write")))
        return dict(base, kind="target", label=_("Target date"), who=self.lawyer_id.name or "", can_act=False)

    def _ldm_cockpit_phases(self):
        """Court stages as a rail: done, current, still to come. No percentage:
        a lawsuit is not a progress bar."""
        self.ensure_one()
        labels = dict(COURT_STAGES)
        current = self.court_stage or "first_instance"
        current_index = PHASE_ORDER.index(current) if current in PHASE_ORDER else 0
        closed = self.state == "done"
        phases = []
        for index, key in enumerate(PHASE_ORDER):
            line = self.court_stage_ids.filtered(lambda s, k=key: s.stage == k)[-1:]
            if index < current_index or (closed and index == current_index):
                status = "done"
            elif index == current_index:
                status = "current"
            else:
                status = "todo"
            phases.append({
                "key": key,
                "label": labels[key],
                "status": status,
                "case_number": line.case_number or "",
                "court": line.department_id.name or "",
            })
        return phases

    # ------------------------------------------------------------------
    # Approvals inbox (S7): the read-only preview beside the list
    # ------------------------------------------------------------------
    def ldm_approval_preview(self):
        self.ensure_one()
        task = self
        kinds = dict(self._fields["kind"]._description_selection(self.env))
        docs = task.document_ids.filtered(lambda d: d.state != "not_needed")
        return {
            "id": task.id,
            "number": task.task_number or "",
            "title": task.name,
            "client": task.legal_company_id.name or "",
            "type": task.template_id.name or kinds.get(task.kind, ""),
            "body": task.department_id.name or "",
            "responsible": task.lawyer_id.name or "",
            "requested_by": task.approval_requested_by_id.name or "",
            "since": iso(task.ldm_waiting_since),
            "value": task.matter_value or 0.0,
            "currency_id": task.currency_id.id,
            "due_date": iso(task.due_date),
            "urgent": task.is_urgent,
            "confidential": task.confidential,
            "steps": [{"name": s.name, "date": iso(s.date_due), "visit": s.is_visit}
                      for s in task.step_ids.filtered(lambda s: s.state == "todo")[:8]],
            "documents": {"have": len(docs.filtered(lambda d: d.state in ("received", "verified"))),
                          "total": len(docs)},
            "approval_state": task.approval_state,
            "can_decide": task.ldm_can_decide,
        }

    # ------------------------------------------------------------------
    # Documents: a file dropped on the cockpit
    # ------------------------------------------------------------------
    def ldm_attach_document(self, document_id, attachment_ids):
        """Attach uploaded files to one document to collect (it becomes
        received), or, without a document, to the matter's other files."""
        self.ensure_one()
        self.check_access("write")
        attachments = self.env["ir.attachment"].browse(attachment_ids).exists()
        attachments = attachments.filtered(lambda a: a.res_model == "legal.task" and a.res_id == self.id)
        if not attachments:
            raise UserError(_("The file did not reach the server. Try again."))
        if document_id:
            document = self.document_ids.filtered(lambda d: d.id == document_id)
            if not document:
                raise UserError(_("That document is not on %s.", self.display_name))
            values = {"attachment_id": attachments[0].id}
            if document.state in ("missing", "expired"):
                values.update(state="received", received_date=fields.Date.context_today(self))
            document.write(values)
            self.message_post(body=_("File attached to “%s”.", document.name), attachment_ids=attachments.ids)
            return {"document": document.name, "state": document.state}
        self.write({"attachment_ids": [(4, a.id) for a in attachments]})
        return {"document": False, "state": False}

    # ------------------------------------------------------------------
    # Agenda (S8): sessions, counter visits and deadlines by day
    # ------------------------------------------------------------------
    @api.model
    def ldm_get_agenda(self, scope="me", days=14):
        days = max(1, min(int(days or 14), 31))
        today = fields.Date.context_today(self)
        end = today + timedelta(days=days - 1)
        if scope not in ("me", "all"):
            scope = "me"
        items = self._ldm_agenda_items(today, end, scope)
        by_day = {}
        for item in items:
            by_day.setdefault(item["date"], []).append(item)
        out = [{"date": day, "items": sorted(rows, key=lambda r: (r["order"], r["time"] or 99, r["label"]))}
               for day, rows in sorted(by_day.items())]
        roll = self.env.ref("legal_department_management.action_report_ldm_hearing_roll", raise_if_not_found=False)
        return {
            "scope": scope,
            "start": iso(today),
            "end": iso(end),
            "days": out,
            "count": len(items),
            "can_print_roll": bool(roll),
        }

    @api.model
    def _ldm_agenda_items(self, start, end, scope, limit=300):
        uid = self.env.uid
        mine = scope == "me"
        items = []
        Hearing = self.env["legal.hearing"]
        domain = [("state", "=", "planned"), ("date", ">=", start), ("date", "<=", end),
                  ("task_id.state", "in", OPEN_STATES)]
        if mine:
            domain += ["|", ("attending_user_id", "=", uid),
                       "&", ("attending_user_id", "=", False), ("task_id.lawyer_id", "=", uid)]
        for hearing in Hearing.search(domain, order="date, time", limit=limit):
            task = hearing.task_id
            items.append({
                "key": f"hearing-{hearing.id}", "kind": "hearing", "order": 0, "id": hearing.id,
                "date": iso(hearing.date), "time": hearing.time or 0.0,
                "label": hearing.department_id.name or task.department_id.name or _("Court session"),
                "subject": task.name, "number": task.task_number or "", "task_id": task.id,
                "who": hearing.attending_user_id.name or "", "unstaffed": not hearing.attending_user_id,
                "open": open_matter(task),
            })
        Step = self.env["legal.task.step"]
        domain = [("state", "=", "todo"), ("is_visit", "=", True), ("date_due", ">=", start), ("date_due", "<=", end),
                  ("task_id.state", "in", OPEN_STATES)]
        if mine:
            domain += ["|", ("user_id", "=", uid), "&", ("user_id", "=", False), ("task_id.lawyer_id", "=", uid)]
        for step in Step.search(domain, order="date_due, sequence", limit=limit):
            task = step.task_id
            items.append({
                "key": f"visit-{step.id}", "kind": "visit", "order": 1, "id": step.id,
                "date": iso(step.date_due), "time": 0.0,
                "label": step.name, "body": step.department_id.name or task.department_id.name or "",
                "subject": task.name, "number": task.task_number or "", "task_id": task.id,
                "who": step.user_id.name or "", "open": open_matter(task),
            })
        Deadline = self.env["legal.deadline"]
        domain = [("state", "=", "open"), ("date_safe", ">=", start), ("date_safe", "<=", end)]
        if mine:
            domain += ["|", ("user_id", "=", uid), "&", ("user_id", "=", False), ("task_id.lawyer_id", "=", uid)]
        for deadline in Deadline.search(domain, order="date_safe", limit=limit):
            task = deadline.task_id
            items.append({
                "key": f"deadline-{deadline.id}", "kind": "deadline", "order": 2, "id": deadline.id,
                "date": iso(deadline.date_safe), "time": 0.0,
                "label": deadline.name, "subject": task.name if task else (deadline.legal_company_id.name or ""),
                "number": task.task_number or "" if task else "", "task_id": task.id or False,
                "who": deadline.user_id.name or "",
                "open": open_matter(task) if task else {"res_model": "legal.deadline", "res_id": deadline.id},
            })
        return items

    @api.model
    def ldm_agenda_calendar_action(self):
        """The native session calendar (month and week), behind the agenda's
        "Month" button."""
        return {
            "type": "ir.actions.act_window",
            "name": _("Court sessions"),
            "res_model": "legal.hearing",
            "views": [[False, "calendar"], [False, "list"], [False, "form"]],
            "domain": [("state", "!=", "cancelled")],
        }

    @api.model
    def ldm_agenda_print_roll(self, date_from, date_to, scope="all"):
        """Print the hearing roll for the agenda's range, when the litigation
        stream's roll report is installed."""
        report = self.env.ref("legal_department_management.action_report_ldm_hearing_roll", raise_if_not_found=False)
        if not report:
            raise UserError(_("The hearing roll is not available in this version."))
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        if report.model == "legal.hearing":
            domain = [("state", "=", "planned"), ("date", ">=", date_from), ("date", "<=", date_to)]
            if scope == "me":
                domain += ["|", ("attending_user_id", "=", self.env.uid),
                           "&", ("attending_user_id", "=", False), ("task_id.lawyer_id", "=", self.env.uid)]
            hearings = self.env["legal.hearing"].search(domain, order="date, time")
            if not hearings:
                raise UserError(_("No court session is planned in these dates."))
            return report.report_action(hearings)
        return report.report_action(None, data={"date_from": iso(date_from), "date_to": iso(date_to)})

    # ------------------------------------------------------------------
    # Command palette: "Record session outcome" on the open matter
    # ------------------------------------------------------------------
    def ldm_palette_record_outcome(self):
        self.ensure_one()
        return self.action_ldm_record_outcome()

    def ldm_row_payload(self):
        """A matter as the palette and the dossier list it."""
        states = dict(self._fields["state"]._description_selection(self.env))
        return [{
            "id": task.id,
            "number": task.task_number or "",
            "title": task.name,
            "line": matter_line(task),
            "state": task.state,
            "state_label": states.get(task.state, ""),
            "next_date": iso(task.next_date),
            "next_action": task.next_action or "",
            "urgent": task.is_urgent,
        } for task in self]

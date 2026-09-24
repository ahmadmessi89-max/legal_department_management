# -*- coding: utf-8 -*-
"""The company file's service overview (design-direction.md, "the company
file is scanned body by body").

Built on G's ``legal.company.coverage`` view: every service tracked for all
companies, grouped by the body that provides it, each with a status, a date,
a responsible person and Start / Open. Read as the user: coverage rows follow
the client's visibility, and a matter the reader may not open is shown only
as a state, never by number or title.
"""
from odoo import _, api, fields, models

from .ws_common import iso

OPEN_TASK_STATES = ("draft", "in_progress", "pending_docs")


class LegalCompany(models.Model):
    _inherit = "legal.company"

    ldm_service_overview = fields.Json(string="Service overview", compute="_compute_ldm_service_overview")

    @api.depends_context("uid", "lang", "tz")
    def _compute_ldm_service_overview(self):
        for client in self:
            client.ldm_service_overview = client._ldm_service_overview_payload() if client.id else {}

    def ldm_get_service_overview(self):
        """The overview of one client, for the OWL panel and the tests."""
        self.ensure_one()
        self.check_access("read")
        return self._ldm_service_overview_payload()

    def _ldm_service_overview_payload(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        user = self.env.user
        can_start = user.has_group("legal_department_management.group_ldm_clerk") and not user.has_group(
            "legal_department_management.group_ldm_auditor")
        rows = self.env["legal.company.coverage"].search([("legal_company_id", "=", self.id)])
        if not rows:
            return {"client_id": self.id, "year": today.year, "bodies": [], "totals": _totals([]),
                    "can_start": can_start}

        # The due date of a service not done yet: the client's obligation for
        # that service, when one is recorded (G's schedules).
        obligations = {}
        Obligation = self.env["legal.obligation"]
        if Obligation.has_access("read"):
            for obligation in Obligation.search([("legal_company_id", "=", self.id),
                                                 ("template_id", "in", rows.template_id.ids)],
                                                order="next_date asc"):
                obligations.setdefault(obligation.template_id.id, obligation)

        tasks = rows.last_task_id
        readable = tasks._filtered_access("read") if tasks else tasks

        bodies, order = {}, []
        for row in rows:
            body = row.department_id
            key = body.id or 0
            if key not in bodies:
                bodies[key] = {
                    "id": body.id or False,
                    "name": body.name or _("Other services"),
                    "ministry": body.ministry_id.name or "",
                    "services": [],
                }
                order.append(key)
            bodies[key]["services"].append(self._ldm_service_row(row, readable, obligations.get(row.template_id.id),
                                                                  today, can_start))

        result = []
        for key in order:
            body = bodies[key]
            body.update(_totals(body["services"]))
            result.append(body)
        # Bodies with work to do first (overdue, then not done), the complete ones last.
        result.sort(key=lambda b: (b["id"] is False, -b["overdue"], b["done"] == b["total"], -b["due"], b["name"]))
        return {
            "client_id": self.id,
            "year": today.year,
            "bodies": result,
            "totals": _totals([s for b in result for s in b["services"]]),
            "can_start": can_start,
        }

    def ldm_action_coverage_register(self):
        """G's register of services this year, for every client, opened on this one."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "legal_department_management.action_ldm_company_coverage")
        action["context"] = {"search_default_legal_company_id": self.id}
        return action

    def _ldm_service_row(self, row, readable, obligation, today, can_start):
        task = row.last_task_id
        visible = bool(task) and task in readable
        state = row.coverage_state
        date, date_kind = False, ""
        responsible = self.lawyer_id
        if state == "done":
            date, date_kind = row.last_done_date, "done"
        elif state == "open" and visible:
            date, date_kind = task.next_date, "next"
        elif state == "due" and obligation:
            date, date_kind = obligation.next_date, "due"
        if visible and task.lawyer_id:
            responsible = task.lawyer_id
        elif obligation and obligation.lawyer_id:
            responsible = obligation.lawyer_id

        # The meaning of the pill (design-direction.md): green done, ink in
        # hand, amber waiting for documents, red only when a due date passed.
        tone = {"done": "success", "open": "primary", "due": "muted"}[state]
        label = dict(row._fields["coverage_state"]._description_selection(self.env))[state]
        if state == "open" and row.last_state == "pending_docs":
            tone, label = "warning", _("Waiting for documents")
        elif state == "open" and row.last_state == "draft":
            tone, label = "info", _("Not started yet")
        overdue = state == "due" and bool(date) and date < today
        if overdue:
            tone, label = "danger", _("Overdue")
        return {
            "coverage_id": row.id,
            "template_id": row.template_id.id,
            "name": row.template_id.name,
            "state": state,
            "tone": tone,
            "label": label,
            "overdue": overdue,
            "date": iso(date),
            "date_kind": date_kind,
            "responsible": {"id": responsible.id, "name": responsible.name} if responsible else False,
            "task_id": task.id if visible else False,
            "task_number": task.task_number if visible else "",
            "can_start": can_start and state == "due",
            "can_open": visible,
        }


def _totals(services):
    return {
        "total": len(services),
        "done": sum(1 for s in services if s["state"] == "done"),
        "open": sum(1 for s in services if s["state"] == "open"),
        "due": sum(1 for s in services if s["state"] == "due"),
        "overdue": sum(1 for s in services if s.get("overdue")),
    }

# -*- coding: utf-8 -*-
"""The client dossier (SPEC 5.5): what is happening now, and one window per
government body or court. Replaces SAG's ``department_cards_html`` blob with
data the OWL panel renders, counted as the reader so a lawyer never learns of
a matter they cannot open."""
from odoo import _, api, fields, models

from .ws_common import OPEN_STATES, iso


class LegalCompany(models.Model):
    _inherit = "legal.company"

    ldm_dossier = fields.Json(string="Dossier", compute="_compute_ldm_dossier")

    @api.depends_context("uid", "lang", "tz")
    def _compute_ldm_dossier(self):
        Task = self.env["legal.task"]
        today = fields.Date.context_today(self)
        for client in self:
            if not client.id:
                client.ldm_dossier = {}
                continue
            base = [("legal_company_id", "=", client.id)]
            urgent = Task.search(base + [("state", "in", OPEN_STATES)],
                                 order="is_urgent desc, next_date asc, id desc", limit=40)
            # Matters with a date first, the earliest first; undated ones last.
            urgent = urgent.sorted(lambda t: (not t.is_urgent, not t.next_date, t.next_date or today, -t.id))[:5]
            now = []
            for row, task in zip(urgent.ldm_row_payload(), urgent):
                row["days"] = (task.next_date - today).days if task.next_date else None
                now.append(row)
            opened = {dept.id: (count, next_date) for dept, count, next_date in Task._read_group(
                base + [("state", "in", OPEN_STATES), ("department_id", "!=", False)],
                ["department_id"], ["__count", "next_date:min"])}
            done = {dept.id: count for dept, count in Task._read_group(
                base + [("state", "=", "done"), ("department_id", "!=", False)], ["department_id"], ["__count"])}
            bodies = []
            for dept in self.env["legal.department"].browse(sorted(set(opened) | set(done))):
                count, next_date = opened.get(dept.id, (0, False))
                bodies.append({
                    "id": dept.id,
                    "name": dept.name,
                    "ministry": dept.ministry_id.name or "",
                    "kind": dept.body_kind,
                    "open": count,
                    "done": done.get(dept.id, 0),
                    "next_date": iso(next_date),
                    "days": (next_date - today).days if next_date else None,
                })
            bodies.sort(key=lambda b: (-b["open"], b["next_date"] or "9999", b["name"]))
            client.ldm_dossier = {
                "client_id": client.id,
                "now": now,
                "open_total": sum(b["open"] for b in bodies) or len(urgent),
                "bodies": bodies,
                "labels": {
                    "now": _("What is happening now"),
                    "bodies": _("By body and court"),
                },
            }

    def ldm_action_sessions(self):
        """The client's planned court sessions (the dossier's stat button)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Court sessions of %s", self.name),
            "res_model": "legal.hearing",
            "views": [[False, "list"], [False, "form"]],
            "domain": [("legal_company_id", "=", self.id), ("state", "=", "planned")],
            "context": {"create": False},
        }

    def ldm_open_matters(self, department_id=False, state="open"):
        """Open the register filtered to this client, and to one body when a
        body window is clicked."""
        self.ensure_one()
        action = self.action_view_tasks()
        domain = [("legal_company_id", "=", self.id)]
        if department_id:
            domain.append(("department_id", "=", department_id))
            department = self.env["legal.department"].browse(department_id)
            action["name"] = f"{self.name} · {department.name}"
        action["domain"] = domain
        context = dict(action.get("context") or {})
        context["search_default_filter_open"] = 1 if state == "open" else 0
        action["context"] = context
        return action

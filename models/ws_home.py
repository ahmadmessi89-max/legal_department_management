# -*- coding: utf-8 -*-
"""The first screen as a dashboard with actions (the owner, 25 September 2026:
"a dashboard in the start with actions ... things to press to take you
places, see things", as SAG's mockup opened).

Three parts are added to My Day's payload, all decided on the server as the
reading user, so nobody is offered a door they cannot open:

* ``actions``: what this role starts from, verbs first (open a matter, record
  a session, write a letter), then the places it goes to most. Each carries
  where it leads and, when it has one, how many things wait there.
* ``tiles``: the counts this role watches. Every tile opens exactly what it
  counted: a band of the work list on this screen, or a list of records
  whose domain is the one that was counted.
* ``glance``: for those who oversee (managers, auditors), where the open work
  is, by kind, by lawyer and by body, each bar opening its matters.
"""
from datetime import timedelta

from odoo import api, models

from .ws_common import OPEN_STATES, iso

# Labels go through self.env._(): several are written inside helper functions,
# where the plain _() cannot find the reader's language in the calling frame.

GLANCE_ROWS = 6


class LegalTask(models.Model):
    _inherit = "legal.task"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _ldm_home_can_read(self, model):
        return model in self.env and self.env[model].has_access("read")

    def _ldm_home_can_create(self, model):
        return model in self.env and self.env[model].has_access("create")

    def _ldm_home_action_ok(self, xmlid):
        """An action this user may open: it exists, its model is readable and,
        when it names groups, the user is in one of them."""
        action = self.env.ref(f"legal_department_management.{xmlid}", raise_if_not_found=False)
        if not action:
            return False
        action = action.sudo()
        groups = action.group_ids if "group_ids" in action._fields else self.env["res.groups"]
        if groups and not (groups & self.env.user.all_group_ids):
            return False
        model = getattr(action, "res_model", False)
        return not model or self._ldm_home_can_read(model)

    def _ldm_home_who(self, ctx, lawyer="lawyer_id", team="lawyer_ids"):
        """The matters the chosen scope covers (the same rule as the work list)."""
        uid = self.env.uid
        if ctx["scope"] == "me" and not ctx["read_only"]:
            return ["|", (lawyer, "=", uid), (team, "in", [uid])]
        if ctx["scope"] == "team":
            return [(team, "in", [uid])]
        return []

    def _ldm_home_sessions_domain(self, ctx, start, end):
        domain = [("state", "=", "planned"), ("task_id.state", "in", list(OPEN_STATES))]
        if start:
            domain.append(("date", ">=", iso(start)))
        if end:
            domain.append(("date", "<=", iso(end)))
        uid = self.env.uid
        if ctx["scope"] == "me" and not ctx["read_only"]:
            domain += ["|", ("attending_user_id", "=", uid),
                       "&", ("attending_user_id", "=", False), ("task_id.lawyer_id", "=", uid)]
        elif ctx["scope"] == "team":
            domain += [("task_id.lawyer_ids", "in", [uid])]
        return domain

    def _ldm_home_deadlines_domain(self, ctx, end):
        domain = [("state", "=", "open"), ("date_safe", "!=", False), ("date_safe", "<=", iso(end))]
        uid = self.env.uid
        if ctx["scope"] == "me" and not ctx["read_only"]:
            domain += ["|", ("user_id", "=", uid), "&", ("user_id", "=", False), ("task_id.lawyer_id", "=", uid)]
        elif ctx["scope"] == "team":
            domain += [("task_id.lawyer_ids", "in", [uid])]
        return domain

    # Domains are built before the call that labels them: Odoo's string
    # extractor reads a domain written inline after a self.env._() in the same call as
    # terms to translate.
    @staticmethod
    def _ldm_home_list(model, domain, name, view="list"):
        return {"type": "list", "model": model, "domain": domain, "name": name, "view": view}

    def _ldm_home_count(self, model, domain):
        return self.env[model].search_count(domain) if self._ldm_home_can_read(model) else 0

    # ------------------------------------------------------------------
    # Actions: what this role starts from
    # ------------------------------------------------------------------
    def _ldm_md_actions(self, ctx, payload):
        role = payload["header"]["role"]
        today = ctx["today"]
        out = []

        def add(key, label, icon, target, count=None, hint=""):
            out.append({"key": key, "label": label, "icon": icon, "target": target,
                        "count": count, "hint": hint})

        def new_matter():
            if payload["can_create"]:
                add("new_matter", self.env._("New matter"), "folder-plus",
                    {"type": "wizard", "xmlid": "action_legal_task_create_wizard"},
                    hint=self.env._("Type, client and key date; the steps fill in"))

        def outcome():
            if ctx["is_lawyer"] and self._ldm_home_can_read("legal.hearing"):
                domain = self._ldm_home_sessions_domain(ctx, False, today)
                add("outcome", self.env._("Record a session"), "gavel",
                    self._ldm_home_list("legal.hearing", domain, self.env._("Sessions to record")),
                    count=self.env["legal.hearing"].search_count(domain),
                    hint=self.env._("What happened, and the next date"))

        def new_letter(direction="outgoing"):
            if self._ldm_feature("group_ldm_correspondence") and self._ldm_home_can_create("legal.correspondence"):
                label = self.env._("Register a letter") if direction == "incoming" else self.env._("Write a letter")
                add("letter", label, "mail-plus",
                    {"type": "form", "model": "legal.correspondence", "name": label,
                     "context": {"default_direction": direction}},
                    hint=self.env._("Numbered in the register"))

        def place(key, xmlid, label, icon, count=None, hint=""):
            """A place the role goes to. Without a label, the action's own name,
            which the vocabulary setting has already made Clients or Companies."""
            if self._ldm_home_action_ok(xmlid):
                label = label or self.env.ref(f"legal_department_management.{xmlid}").name
                add(key, label, icon, {"type": "action", "xmlid": xmlid}, count=count, hint=hint)

        def approvals():
            chip = payload.get("approvals")
            if chip:
                place("approvals", "action_legal_task_to_approve", self.env._("Approvals"), "stamp",
                      count=chip["count"], hint=self.env._("Matters waiting for your decision"))

        if role == "manager":
            new_matter()
            outcome()
            new_letter()
            place("agenda", "action_ldm_agenda_board", self.env._("Agenda"), "calendar-days")
            approvals()
            place("analytics", "action_ldm_analytics", self.env._("Analytics"), "chart-column")
        elif role == "lawyer":
            new_matter()
            outcome()
            new_letter()
            place("agenda", "action_ldm_agenda_board", self.env._("Agenda"), "calendar-days")
            place("poa", "action_ldm_poa", self.env._("Powers of attorney"), "file-signature")
            place("clients", "action_legal_company", None, "building-2")
        elif role == "approver":
            approvals()
            new_matter()
            place("matters", "action_legal_task", self.env._("Matters"), "folder-open")
            place("agenda", "action_ldm_agenda_board", self.env._("Agenda"), "calendar-days")
            place("clients", "action_legal_company", None, "building-2")
        elif role == "clerk":
            new_matter()
            visits = sum(len(group["visits"]) for group in payload["by_body"])
            if visits:
                add("visits", self.env._("Today's visits"), "route", {"type": "anchor", "ref": "route"}, count=visits,
                    hint=self.env._("Body by body, with what to carry"))
            new_letter("incoming")
            place("bodies", "action_ldm_body_directory", self.env._("Bodies and courts"), "landmark")
            place("advances", "action_ldm_advance", self.env._("Cash advances"), "wallet")
            place("agenda", "action_ldm_agenda_board", self.env._("Agenda"), "calendar-days")
        elif role == "auditor":
            place("analytics", "action_ldm_analytics", self.env._("Analytics"), "chart-column")
            place("matters", "action_legal_task", self.env._("Matters"), "folder-open")
            if self._ldm_feature("group_ldm_correspondence"):
                place("correspondence", "action_ldm_correspondence", self.env._("Correspondence"), "mail")
            place("deadlines", "action_ldm_deadline", self.env._("Deadlines"), "hourglass")
            place("report", "action_legal_general_report_wizard", self.env._("Oversight report"), "printer")
            place("agenda", "action_ldm_agenda_board", self.env._("Agenda"), "calendar-days")
        elif role == "billing":
            if self._ldm_home_can_read("legal.engagement.line"):
                due = self.env["legal.engagement.line"].search_count([("state", "=", "due")])
                place("to_invoice", "action_ldm_to_invoice", self.env._("To invoice"), "receipt", count=due,
                      hint=self.env._("Due fees, ready for an invoice"))
            place("engagements", "action_ldm_engagement", self.env._("Fee agreements"), "file-signature")
            place("client_money", "action_ldm_client_fund", self.env._("Client money"), "hand-coins")
            if self._ldm_feature("group_ldm_time"):
                place("time", "action_ldm_time_entry", self.env._("Time"), "clock")
            place("clients", "action_legal_company", None, "building-2")
        # The first is the one primary action of the screen.
        for index, action in enumerate(out[:6]):
            action["primary"] = index == 0
        return out[:6]

    # ------------------------------------------------------------------
    # Tiles: the counts this role watches
    # ------------------------------------------------------------------
    def _ldm_md_tiles(self, ctx, payload):
        role = payload["header"]["role"]
        today = ctx["today"]
        week_end = today + timedelta(days=6)
        bands = {band["key"]: band for band in payload["bands"]}
        tiles = []

        def band_tile(key, hint, tone):
            band = bands.get(key)
            tiles.append({"key": key, "label": band["title"] if band else key, "count": band["count"] if band else 0,
                          "hint": hint, "tone": tone, "icon": {"overdue": "triangle-alert", "today": "circle-dot",
                                                               "week": "calendar-clock"}[key],
                          "target": {"type": "band", "band": key}})

        def list_tile(key, label, icon, model, domain, hint="", tone="neutral", name=None, amount=None,
                      currency_id=None):
            if not self._ldm_home_can_read(model):
                return
            tile = {"key": key, "label": label, "count": self.env[model].search_count(domain), "hint": hint,
                    "tone": tone, "icon": icon, "target": self._ldm_home_list(model, domain, name or label)}
            if amount is not None:
                tile.update(amount=amount, currency_id=currency_id)
            tiles.append(tile)

        open_domain = [("state", "in", list(OPEN_STATES))] + self._ldm_home_who(ctx)

        def sessions():
            list_tile("sessions", self.env._("Court sessions this week"), "gavel", "legal.hearing",
                      self._ldm_home_sessions_domain(ctx, today, week_end), hint=self.env._("In court in the next seven days"),
                      tone="info")

        def periods():
            list_tile("periods", self.env._("Legal periods ending"), "hourglass", "legal.deadline",
                      self._ldm_home_deadlines_domain(ctx, week_end), hint=self.env._("Last safe day within a week"),
                      tone="warning")

        def open_matters(label=None):
            list_tile("open", label or self.env._("Open matters"), "folder-open", "legal.task", open_domain,
                      hint=self.env._("Of every kind"))

        def approvals():
            if self._ldm_feature("group_ldm_approvals"):
                waiting = [("approval_state", "=", "to_approve")]
                list_tile("approval", self.env._("Awaiting approval"), "stamp", "legal.task", waiting,
                          hint=self.env._("Sent to an approver"), tone="info")

        if role in ("manager", "lawyer", "approver", "clerk"):
            band_tile("overdue", self.env._("Past their date"), "danger")
            band_tile("today", self.env._("Due today"), "warning")
        if role == "manager":
            sessions()
            periods()
            approvals()
            open_matters()
        elif role == "lawyer":
            band_tile("week", self.env._("In the next six days"), "neutral")
            sessions()
            periods()
            open_matters(self.env._("My open matters"))
        elif role == "approver":
            band_tile("week", self.env._("In the next six days"), "neutral")
            approvals()
        elif role == "clerk":
            visits = sum(len(group["visits"]) for group in payload["by_body"])
            tiles.append({"key": "visits", "label": self.env._("Visits today"), "count": visits,
                          "hint": self.env._("Counters to go to"), "tone": "info", "icon": "route",
                          "target": {"type": "anchor", "ref": "route"}})
            for entry in payload["advance"][:1]:
                tiles.append({"key": "advance", "label": entry["label"], "count": None, "amount": entry["amount"],
                              "currency_id": entry["currency_id"], "hint": self.env._("Settle it against receipts"),
                              "tone": "warning", "icon": "wallet",
                              "target": self._ldm_home_list("legal.advance", [("user_id", "=", self.env.uid),
                                                                              ("state", "=", "paid")],
                                                            self.env._("Cash advances"))})
            if self._ldm_feature("group_ldm_government"):
                expiring = [("date_expiry", "!=", False), ("date_expiry", ">=", iso(today)),
                            ("date_expiry", "<=", iso(today + timedelta(days=30)))]
                list_tile("expiring", self.env._("Documents expiring"), "file-clock", "legal.company.document", expiring,
                          hint=self.env._("In the next thirty days"), tone="warning")
            open_matters(self.env._("My open matters"))
        elif role == "auditor":
            open_matters()
            list_tile("late", self.env._("Matters past their date"), "triangle-alert", "legal.task",
                      open_domain + [("next_date", "<", iso(today))], hint=self.env._("Their next date has passed"),
                      tone="danger")
            sessions()
            periods()
            approvals()
            if hasattr(self, "_ldm_past_target_domain") and self._ldm_feature("group_ldm_government"):
                list_tile("past_target", self.env._("At a body past target"), "landmark", "legal.task",
                          self._ldm_past_target_domain(), hint=self.env._("Longer than the body usually takes"),
                          tone="warning")
        elif role == "billing":
            self._ldm_home_billing_tiles(tiles, list_tile, today)
        return tiles[:6]

    def _ldm_home_billing_tiles(self, tiles, list_tile, today):
        Line = self.env["legal.engagement.line"]
        if not Line.has_access("read"):
            return
        due = Line.search([("state", "=", "due")])
        amount, currency = 0.0, self.env.company.currency_id
        for line in due:
            if line.currency_id == currency:
                amount += line.amount
        due_domain = [("state", "=", "due")]
        late_domain = [("state", "=", "due"), ("date", "<", iso(today))]
        active_domain = [("state", "=", "active")]
        time_domain = [("billable", "=", True), ("state", "!=", "invoiced")]
        list_tile("to_invoice", self.env._("To invoice"), "receipt", "legal.engagement.line", due_domain,
                  hint=self.env._("Due fee lines"), tone="info", amount=amount, currency_id=currency.id)
        list_tile("late_fees", self.env._("Instalments overdue"), "triangle-alert", "legal.engagement.line", late_domain,
                  hint=self.env._("Due before today, not invoiced"), tone="danger")
        list_tile("engagements", self.env._("Active fee agreements"), "file-signature", "legal.engagement", active_domain,
                  hint=self.env._("Signed and running"))
        if self._ldm_feature("group_ldm_time"):
            list_tile("time", self.env._("Time to invoice"), "clock", "legal.time.entry", time_domain,
                      hint=self.env._("Billable, not invoiced yet"))

    # ------------------------------------------------------------------
    # At a glance: where the open work is (those who oversee)
    # ------------------------------------------------------------------
    def _ldm_md_glance(self, ctx):
        if not (ctx["is_manager"] or ctx["read_only"]) or not self._ldm_home_can_read("legal.task"):
            return []
        today = ctx["today"]
        base = [("state", "in", list(OPEN_STATES))] + self._ldm_home_who(ctx)
        panels = []

        kinds = dict(self._fields["kind"]._description_selection(self.env))
        rows = []
        for kind, count in self._read_group(base, ["kind"], ["__count"], order="__count desc"):
            rows.append({"key": kind or "none", "label": kinds.get(kind, self.env._("Other")), "count": count,
                         "domain": base + [("kind", "=", kind)]})
        panels.append({"key": "kind", "title": self.env._("By kind"), "rows": rows[:GLANCE_ROWS]})

        late = {user.id: count for user, count in self._read_group(
            base + [("next_date", "<", iso(today))], ["lawyer_id"], ["__count"])}
        rows = []
        for user, count in self._read_group(base, ["lawyer_id"], ["__count"], order="__count desc"):
            rows.append({"key": user.id or 0, "label": user.name or self.env._("Nobody yet"), "count": count,
                         "late": late.get(user.id, 0), "domain": base + [("lawyer_id", "=", user.id or False)]})
        panels.append({"key": "lawyer", "title": self.env._("By lawyer"), "rows": rows[:GLANCE_ROWS],
                       "legend": self.env._("Past their date")})

        rows = []
        for body, count in self._read_group(base + [("department_id", "!=", False)], ["department_id"],
                                            ["__count"], order="__count desc", limit=GLANCE_ROWS):
            rows.append({"key": body.id, "label": body.name, "count": count,
                         "domain": base + [("department_id", "=", body.id)]})
        panels.append({"key": "body", "title": self.env._("By body or court"), "rows": rows})
        for panel in panels:
            top = max([row["count"] for row in panel["rows"]] or [0])
            for row in panel["rows"]:
                row["share"] = round(100.0 * row["count"] / top, 1) if top else 0
        return [panel for panel in panels if panel["rows"]]

    @api.model
    def _ldm_md_home(self, ctx, payload):
        """The dashboard parts of the first screen (see the module docstring)."""
        payload["actions"] = self._ldm_md_actions(ctx, payload)
        payload["tiles"] = self._ldm_md_tiles(ctx, payload)
        # Where the work is: for those who oversee it (managers, auditors).
        oversees = payload["header"]["role"] in ("manager", "auditor")
        payload["glance"] = self._ldm_md_glance(ctx) if oversees else []
        return payload

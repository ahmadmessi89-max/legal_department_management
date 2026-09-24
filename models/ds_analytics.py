# -*- coding: utf-8 -*-
"""The managers' analytics board (design-direction.md, "Charts").

One server call answers the questions a legal manager asks of the team, from
the records the reader may see (every query runs as the user, so record rules
and companies apply; nothing is read with sudo), and every figure carries the
domain of the records it counts, so a bar or a number opens exactly those
matters. Lists are bounded: at most ten bodies, types or roles, fifteen
people, five clients (the rest summed as "Other clients") and twelve months.
Money is in the company currency; IQD is shown in whole dinars by the board.
"""
import bisect
import statistics
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .legal_task_template import MATTER_KINDS

OPEN_STATES = ("draft", "in_progress", "pending_docs")
TOP = 10
TOP_PEOPLE = 15
TOP_CLIENTS = 5
PERIODS = ("month", "quarter", "year", "12m")


def _iso(day):
    return fields.Date.to_string(day)


def _period_bounds(period, today):
    if period == "month":
        return today.replace(day=1), today
    if period == "quarter":
        return (today - relativedelta(months=2)).replace(day=1), today
    if period == "12m":
        return (today - relativedelta(months=11)).replace(day=1), today
    return date(today.year, 1, 1), today


def _months(first, last):
    """First days of the months from ``first`` to ``last``."""
    months, current = [], first.replace(day=1)
    while current <= last and len(months) < 12:
        months.append(current)
        current = current + relativedelta(months=1)
    return months


class LegalTask(models.Model):
    _inherit = "legal.task"

    @api.model
    def _ldm_check_analytics_access(self):
        user = self.env.user
        if not (self.env.su or user.has_group("legal_department_management.group_legal_manager")
                or user.has_group("legal_department_management.group_ldm_auditor")):
            raise AccessError(_("The analytics board is for legal managers and auditors."))

    @api.model
    def ldm_analytics(self, period="year"):
        """The whole board in one payload (see the module docstring)."""
        self._ldm_check_analytics_access()
        period = period if period in PERIODS else "year"
        today = fields.Date.context_today(self)
        first, last = _period_bounds(period, today)
        company = self.env.company
        currency = company.currency_id
        board = _Board(self, company, today, first, last)
        return {
            "period": period,
            "periods": [
                {"key": "month", "label": _("This month")},
                {"key": "quarter", "label": _("Last 3 months")},
                {"key": "year", "label": _("This year")},
                {"key": "12m", "label": _("Last 12 months")},
            ],
            "date_from": _iso(first),
            "date_to": _iso(last),
            "company": company.name,
            "currency": {"id": currency.id, "name": currency.name, "symbol": currency.symbol,
                         "position": currency.position, "whole": currency.name == "IQD",
                         "digits": 0 if currency.name == "IQD" else currency.decimal_places},
            "figures": board.figures(),
            "charts": {
                "by_body": board.open_by_body(),
                "by_kind": board.open_by_kind(),
                "workload": board.workload(),
                "time_to_close": board.time_to_close(),
                "deadlines": board.deadlines(),
                "past_target": board.past_target(),
                "expenses": board.expenses(),
                "exposure": board.exposure(),
            },
        }


class _Board:
    """The queries behind the board, as the reading user."""

    def __init__(self, Task, company, today, first, last):
        self.env = Task.env
        self.Task = Task
        self.company = company
        self.today = today
        self.first = first
        self.last = last
        self.base = [("company_id", "=", company.id)]
        self.open = self.base + [("state", "in", list(OPEN_STATES))]
        self.period = [(">=", _iso(first)), ("<=", _iso(last))]

    def _in_period(self, field):
        return [(field, op, value) for op, value in self.period]

    @staticmethod
    def action(model, domain, name):
        return {"model": model, "domain": domain, "name": name}

    # ---------------------------------------------------------------- figures
    def figures(self):
        Task, Deadline = self.Task, self.env["legal.deadline"]
        closed = self.base + [("state", "=", "done")] + self._in_period("date_closed")
        missed = [("company_id", "=", self.company.id), ("state", "=", "missed")] + self._in_period("date_deadline")
        if "our_action" in Deadline._fields:
            missed.append(("our_action", "=", True))
        rows = [
            ("open", _("Open matters"), "legal.task", self.open, ""),
            ("closed", _("Closed in the period"), "legal.task", closed, "success"),
            ("missed", _("Deadlines missed in the period"), "legal.deadline", missed, "danger"),
        ]
        if "ldm_past_target" in Task._fields:
            rows.append(("past_target", _("At the body past target"), "legal.task",
                         self.base + Task._ldm_past_target_domain(), "danger"))
        figures = []
        for key, label, model, domain, tone in rows:
            count = self.env[model].search_count(domain)
            figures.append({"key": key, "label": label, "value": count, "tone": tone if count else "",
                            "action": self.action(model, domain, label)})
        return figures

    # ------------------------------------------------------------- open work
    def open_by_body(self):
        rows = self.Task._read_group(self.open + [("department_id", "!=", False)], ["department_id"], ["__count"],
                                     order="__count desc", limit=TOP)
        items = [{"label": body.display_name, "value": count,
                  "action": self.action("legal.task", self.open + [("department_id", "=", body.id)], body.display_name)}
                 for body, count in rows]
        unbodied = self.Task.search_count(self.open + [("department_id", "=", False)])
        if unbodied:
            label = _("No body or court")
            items.append({"label": label, "value": unbodied,
                          "action": self.action("legal.task", self.open + [("department_id", "=", False)], label)})
        return {"kind": "bars", "unit": "count", "items": items}

    def open_by_kind(self):
        labels = dict(MATTER_KINDS)
        labels.update(dict(self.Task._fields["kind"]._description_selection(self.env)))
        rows = self.Task._read_group(self.open, ["kind"], ["__count"], order="__count desc")
        items = [{"label": labels.get(kind, kind or _("Other")), "value": count, "kind": kind or "other",
                  "action": self.action("legal.task", self.open + [("kind", "=", kind)], labels.get(kind, kind))}
                 for kind, count in rows]
        return {"kind": "bars", "unit": "count", "tone": "kind", "items": items}

    def workload(self):
        states = [("draft", _("New"), "muted"), ("in_progress", _("In progress"), "ink"),
                  ("pending_docs", _("Waiting"), "warning")]
        rows = self.Task._read_group(self.open, ["lawyer_id", "state"], ["__count"])
        totals = {}
        for user, state, count in rows:
            totals[user] = totals.get(user, 0) + count
        people = sorted(totals, key=lambda u: (-totals[u], u.name or ""))[:TOP_PEOPLE]
        cells = {(user, state): count for user, state, count in rows}
        series = []
        for state, label, tone in states:
            values, actions = [], []
            for user in people:
                domain = self.open + [("lawyer_id", "=", user.id or False), ("state", "=", state)]
                values.append(cells.get((user, state), 0))
                actions.append(self.action("legal.task", domain, f"{user.name or _('Nobody')} · {label}"))
            series.append({"key": state, "label": label, "tone": tone, "values": values, "actions": actions})
        return {"kind": "stacked", "unit": "count", "horizontal": True,
                "labels": [user.name or _("Nobody") for user in people], "series": series}

    # ------------------------------------------------------------ throughput
    def time_to_close(self):
        domain = self.base + [("state", "=", "done"), ("date_opened", "!=", False)] + self._in_period("date_closed")
        closed = self.Task.search_fetch(domain, ["template_id", "date_opened", "date_closed"], limit=2000)
        if not closed:
            return {"kind": "bars", "unit": "days", "items": []}
        calendar = self.company._ldm_calendar()
        first = min(m.date_opened for m in closed)
        last = max(m.date_closed for m in closed)
        if calendar:
            working = sorted(self.company._ldm_working_days(calendar, first, last))
        else:
            working = [first + timedelta(days=n) for n in range((last - first).days + 1)]
        by_type = {}
        for matter in closed:
            # Working days after the opening day, up to and including the closing day.
            days = bisect.bisect_right(working, matter.date_closed) - bisect.bisect_right(working, matter.date_opened)
            by_type.setdefault(matter.template_id, []).append(max(days, 0))
        ranked = sorted(by_type.items(), key=lambda kv: (-len(kv[1]), kv[0].name or ""))[:TOP]
        items = []
        for template, durations in ranked:
            label = template.name or _("No matter type")
            items.append({
                "label": label,
                "value": statistics.median(durations),
                "count": len(durations),
                "action": self.action("legal.task", domain + [("template_id", "=", template.id or False)], label),
            })
        items.sort(key=lambda i: -i["value"])
        return {"kind": "bars", "unit": "days", "items": items}

    def deadlines(self):
        Deadline = self.env["legal.deadline"]
        ours = [("company_id", "=", self.company.id)]
        if "our_action" in Deadline._fields:
            ours.append(("our_action", "=", True))
        months = _months(self.first, self.last)
        met_domain = ours + [("state", "=", "done")]
        missed_domain = ours + [("state", "=", "missed")]
        # Met counts on the day it was met, missed on the legal last day.
        met_field = "date_done" if "date_done" in Deadline._fields else "date_safe"
        met = dict(Deadline._read_group(met_domain + self._in_period(met_field), [f"{met_field}:month"], ["__count"]))
        missed = dict(Deadline._read_group(missed_domain + self._in_period("date_deadline"), ["date_deadline:month"],
                                           ["__count"]))
        labels, series = [], [
            {"key": "done", "label": _("Met"), "tone": "success", "values": [], "actions": []},
            {"key": "missed", "label": _("Missed"), "tone": "danger", "values": [], "actions": []},
        ]
        for month in months:
            end = month + relativedelta(months=1) - timedelta(days=1)
            label = month.strftime("%Y-%m")
            labels.append(_iso(month))
            for serie, base, field, counts in ((series[0], met_domain, met_field, met),
                                               (series[1], missed_domain, "date_deadline", missed)):
                domain = base + [(field, ">=", _iso(month)), (field, "<=", _iso(end))]
                serie["values"].append(_month_count(counts, month))
                serie["actions"].append(self.action("legal.deadline", domain, f"{serie['label']} · {label}"))
        return {"kind": "stacked", "unit": "count", "months": True, "labels": labels, "series": series}

    def past_target(self):
        if "ldm_past_target" not in self.Task._fields:
            return {"kind": "bars", "unit": "count", "tone": "danger", "items": []}
        domain = self.base + self.Task._ldm_past_target_domain()
        rows = self.Task._read_group(domain, ["department_id"], ["__count"], order="__count desc", limit=TOP)
        items = [{"label": body.display_name or _("No body or court"), "value": count,
                  "action": self.action("legal.task", domain + [("department_id", "=", body.id or False)],
                                        body.display_name or _("No body or court"))}
                 for body, count in rows]
        return {"kind": "bars", "unit": "count", "tone": "danger", "items": items}

    # ----------------------------------------------------------------- money
    def expenses(self):
        Expense = self.env["legal.task.expense"]
        domain = [("company_id", "=", self.company.id), ("state", "=", "confirmed")] + self._in_period("date")
        totals = Expense._read_group(domain, ["legal_company_id"], ["amount_company:sum"],
                                     order="amount_company:sum desc")
        top = [client for client, total in totals if total][:TOP_CLIENTS]
        rows = Expense._read_group(domain, ["date:month", "legal_company_id"], ["amount_company:sum"])
        cells = {}
        for month, client, amount in rows:
            key = client if client in top else None
            cells[(month.replace(day=1), key)] = cells.get((month.replace(day=1), key), 0.0) + (amount or 0.0)
        months = _months(self.first, self.last)
        others = any(key is None for (_m, key) in cells)
        clients = list(top) + ([None] if others else [])
        series = []
        for index, client in enumerate(clients):
            label = client.display_name if client else _("Other clients")
            values, actions = [], []
            for month in months:
                end = month + relativedelta(months=1) - timedelta(days=1)
                month_domain = domain + [("date", ">=", _iso(month)), ("date", "<=", _iso(end))]
                if client:
                    month_domain = month_domain + [("legal_company_id", "=", client.id)]
                else:
                    month_domain = month_domain + [("legal_company_id", "not in", [c.id for c in top])]
                values.append(round(cells.get((month, client), 0.0), 2))
                actions.append(self.action("legal.task.expense", month_domain, f"{label} · {month.strftime('%Y-%m')}"))
            series.append({"key": client.id if client else "others", "label": label, "tone": f"ink{index}",
                           "values": values, "actions": actions})
        return {"kind": "stacked", "unit": "money", "months": True, "labels": [_iso(m) for m in months],
                "series": series, "total": round(sum(total or 0.0 for _c, total in totals), 2)}

    def exposure(self):
        domain = self.open + [("kind", "=", "litigation"), ("our_role", "!=", False)]
        roles = dict(self.Task._fields["our_role"]._description_selection(self.env))
        rows = self.Task._read_group(domain, ["our_role", "currency_id"], ["matter_value:sum", "__count"])
        company_currency = self.company.currency_id
        by_role = {}
        for role, currency, amount, count in rows:
            value = currency._convert(amount or 0.0, company_currency, self.company, self.today) \
                if currency and currency != company_currency else (amount or 0.0)
            entry = by_role.setdefault(role, {"value": 0.0, "count": 0})
            entry["value"] += value
            entry["count"] += count
        brought_by_us = ("plaintiff", "complainant")
        items = []
        for role, entry in sorted(by_role.items(), key=lambda kv: -kv[1]["value"])[:TOP]:
            if not entry["value"]:
                continue
            label = roles.get(role, role)
            items.append({
                "label": label,
                "value": round(entry["value"], 2),
                "count": entry["count"],
                "side": "for" if role in brought_by_us else "against",
                "action": self.action("legal.task", domain + [("our_role", "=", role)], label),
            })
        total_for = sum(i["value"] for i in items if i["side"] == "for")
        total_against = sum(i["value"] for i in items if i["side"] == "against")
        return {"kind": "bars", "unit": "money", "items": items,
                "total_for": round(total_for, 2), "total_against": round(total_against, 2)}


def _month_count(counts, month):
    for key, value in counts.items():
        if key and key.replace(day=1) == month:
            return value
    return 0

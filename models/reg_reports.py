# -*- coding: utf-8 -*-
"""Values for the printed reports.

Every report reads its options from the report ``data`` (never from the
context, which the client does not keep when it builds the report URL) and
finds its records as the person printing, so a report can never show a matter
that person cannot open. A filter that matches nothing prints nothing: the
old client file printed every matter when its filter came back empty."""
from collections import OrderedDict, defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.fields import Domain

from .reg_render import fdate, money, qr_data_uri

OPEN_STATES = ("draft", "in_progress", "pending_docs")
CLOSED_STATES = ("done", "cancelled")
MONEY_GROUPS = ("legal_department_management.group_legal_manager", "legal_department_management.group_ldm_auditor",
                "legal_department_management.group_ldm_billing_user")
NOTE_GROUPS = ("legal_department_management.group_ldm_clerk", "legal_department_management.group_ldm_auditor")


def _state_domain(state):
    if state == "open":
        return Domain("state", "in", OPEN_STATES)
    if state == "closed":
        return Domain("state", "in", CLOSED_STATES)
    if state in ("draft", "in_progress", "pending_docs", "done", "cancelled"):
        return Domain("state", "=", state)
    return Domain.TRUE


def matter_filter_domain(data):
    """The matters a report's options select, as a domain. Shared by the
    client file and the oversight report (and their dialogs)."""
    data = data or {}
    domain = Domain.TRUE
    if data.get("client_ids"):
        domain &= Domain("legal_company_id", "in", data["client_ids"])
    if data.get("lawyer_id"):
        domain &= Domain("lawyer_id", "=", data["lawyer_id"]) | Domain("lawyer_ids", "in", [data["lawyer_id"]])
    if data.get("department_id"):
        domain &= Domain("department_id", "=", data["department_id"])
    domain &= _state_domain(data.get("state"))
    date_from, date_to = data.get("date_from"), data.get("date_to")
    if date_from or date_to:
        def in_range(field):
            part = Domain(field, "!=", False)
            if date_from:
                part &= Domain(field, ">=", date_from)
            if date_to:
                part &= Domain(field, "<=", date_to)
            return part
        domain &= in_range("due_date") | in_range("next_date")
    if data.get("domain"):
        domain &= Domain(data["domain"])
    if data.get("task_ids") is not None:
        domain &= Domain("id", "in", data["task_ids"])
    return domain


class LdmReportMixin(models.AbstractModel):
    _name = "ldm.report.mixin"
    _description = "Helpers for the legal reports"

    def _ldm_helpers(self):
        env = self.env
        user = env.user
        lang = env["res.lang"]._get_data(code=env.lang or user.lang or "en_US")
        base_url = env["ir.config_parameter"].sudo().get_param("web.base.url", "")

        def label(record, field_name):
            if not record:
                return ""
            return dict(record._fields[field_name]._description_selection(env)).get(record[field_name], "") or ""

        return {
            "money": lambda amount, currency=None: money(env, amount, currency),
            "fdate": lambda value: fdate(env, value),
            "label": label,
            "qr": lambda value: qr_data_uri(env, value),
            "ldm_dir": lang.direction or "ltr",
            "today": fields.Date.context_today(self),
            "can_money": any(user.has_group(g) for g in MONEY_GROUPS),
            "can_notes": any(user.has_group(g) for g in NOTE_GROUPS),
            "record_url": lambda record, path: f"{base_url}/odoo/{path}/{record.id}",
        }

    @api.model
    def _ldm_sum_by_currency(self, records, amount_field, currency_field="currency_id"):
        totals = OrderedDict()
        for record in records:
            currency = record[currency_field] or self.env.company.currency_id
            totals[currency] = totals.get(currency, 0.0) + (record[amount_field] or 0.0)
        return list(totals.items())


class ReportFollowUpSheet(models.AbstractModel):
    """استمارة متابعة: the sheet a runner carries to the counter."""

    _name = "report.legal_department_management.report_legal_task_template"
    _table = "ldm_report_followup"  # the model name is longer than a Postgres identifier
    _inherit = "ldm.report.mixin"
    _description = "Matter follow-up sheet"

    @api.model
    def _get_report_values(self, docids, data=None):
        ids = docids or (data or {}).get("ids") or []
        docs = self.env["legal.task"].browse(ids).exists()
        values = self._ldm_helpers()
        values.update(doc_ids=docs.ids, doc_model="legal.task", docs=docs, data=data or {})
        return values


class ReportClientFile(models.AbstractModel):
    """The client file: identifiers, matters by body, what is open, expenses."""

    _name = "report.legal_department_management.report_legal_company_template"
    _table = "ldm_report_client_file"  # the model name is longer than a Postgres identifier
    _inherit = "ldm.report.mixin"
    _description = "Client file"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        ids = data.get("client_ids") or docids or []
        docs = self.env["legal.company"].browse(ids).exists()
        filters = dict(data, client_ids=False)
        base = matter_filter_domain(filters) if data.get("filtered") else Domain.TRUE
        Task = self.env["legal.task"]
        files = {}
        for client in docs:
            tasks = Task.search(base & Domain("legal_company_id", "=", client.id),
                                order="state, next_date, task_number")
            by_body = OrderedDict()
            # Matters without a body come last.
            for task in tasks.sorted(lambda t: (not t.department_id, t.department_id.name or "",
                                                t.next_date or fields.Date.today())):
                by_body.setdefault(task.department_id, Task)
                by_body[task.department_id] |= task
            open_tasks = tasks.filtered(lambda t: t.state in OPEN_STATES)
            open_items = []
            for task in open_tasks:
                for date, _order, text in sorted(task._ldm_open_items(), key=lambda item: (item[0], item[1]))[:3]:
                    open_items.append({"task": task, "date": date, "text": text})
            open_items.sort(key=lambda item: item["date"])
            files[client.id] = {
                "tasks": tasks,
                "by_body": list(by_body.items()),
                "open_count": len(open_tasks),
                "closed_count": len(tasks) - len(open_tasks),
                "open_items": open_items[:25],
                "expenses": self._ldm_sum_by_currency(tasks.expense_ids, "amount"),
            }
        values = self._ldm_helpers()
        values.update(
            doc_ids=docs.ids, doc_model="legal.company", docs=docs, data=data, files=files,
            show_identifiers=data.get("show_company_info", True),
            filter_lines=self._ldm_filter_lines(data),
        )
        return values

    @api.model
    def _ldm_filter_lines(self, data):
        lines = []
        if data.get("lawyer_id"):
            lines.append((_("Responsible"), self.env["res.users"].browse(data["lawyer_id"]).name))
        if data.get("department_id"):
            lines.append((_("Body or court"), self.env["legal.department"].browse(data["department_id"]).name))
        if data.get("state"):
            states = dict(self.env["legal.general.report.wizard"]._fields["filter_state"]._description_selection(
                self.env))
            lines.append((_("Status"), states.get(data["state"], data["state"])))
        if data.get("date_from") or data.get("date_to"):
            lines.append((_("Dates"), " – ".join(filter(None, [
                fdate(self.env, fields.Date.to_date(data.get("date_from"))) if data.get("date_from") else "",
                fdate(self.env, fields.Date.to_date(data.get("date_to"))) if data.get("date_to") else ""]))))
        if data.get("task_ids") is not None:
            lines.append((_("Chosen matters"), str(len(data["task_ids"]))))
        return lines


class ReportOversight(models.AbstractModel):
    """The oversight report across clients, grouped by client when asked."""

    _name = "report.legal_department_management.report_legal_general_overview_template"
    _table = "ldm_report_oversight"  # the model name is longer than a Postgres identifier
    _inherit = "ldm.report.mixin"
    _description = "Oversight report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        Task = self.env["legal.task"]
        if data.get("filtered"):
            tasks = Task.search(matter_filter_domain(data), order="legal_company_id, next_date, task_number")
        else:
            tasks = Task.browse(docids or []).exists()
        group_by_client = data.get("group_by_client", True)
        groups = []
        if group_by_client:
            by_client = OrderedDict()
            for task in tasks.sorted(lambda t: (t.legal_company_id.name or "", t.next_date or fields.Date.today())):
                by_client.setdefault(task.legal_company_id, Task)
                by_client[task.legal_company_id] |= task
            groups = list(by_client.items())
        elif tasks:
            groups = [(False, tasks)]
        clients = data.get("client_ids") and self.env["legal.company"].browse(data["client_ids"])
        values = self._ldm_helpers()
        values.update(
            doc_ids=tasks.ids, doc_model="legal.task", docs=tasks, data=data, tasks=tasks, groups=groups,
            group_by_client=group_by_client,
            open_count=len(tasks.filtered(lambda t: t.state in OPEN_STATES)),
            overdue_count=len(tasks.filtered("is_overdue")),
            client_count=len(tasks.legal_company_id),
            expenses=self._ldm_sum_by_currency(tasks.expense_ids, "amount"),
            scope=", ".join(clients.mapped("name")) if clients else _("All clients"),
            filter_lines=self.env["report.legal_department_management.report_legal_company_template"]
            ._ldm_filter_lines(data),
        )
        return values


class ReportMonthlyStatus(models.AbstractModel):
    """موقف الدعاوى والمعاملات: the monthly status report ministries expect."""

    _name = "report.legal_department_management.report_ldm_monthly_status"
    _table = "ldm_report_monthly"  # the model name is longer than a Postgres identifier
    _inherit = "ldm.report.mixin"
    _description = "Monthly status of lawsuits and transactions"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        today = fields.Date.context_today(self)
        date_to = fields.Date.to_date(data.get("date_to")) or today
        date_from = fields.Date.to_date(data.get("date_from")) or date_to.replace(day=1)
        Task = self.env["legal.task"]

        def within(field):
            return Domain(field, ">=", date_from) & Domain(field, "<=", date_to)

        # Lawsuits for and against.
        lawsuits = Task.search([("kind", "in", ("litigation", "execution"))])
        sides = [
            ("for", _("Brought by us"), ("plaintiff", "complainant")),
            ("against", _("Brought against us"), ("defendant", "accused")),
            ("other", _("Other role or not set"), None),
        ]
        side_rows = []
        for key, title, roles in sides:
            if roles:
                subset = lawsuits.filtered(lambda t, r=roles: t.our_role in r)
            else:
                subset = lawsuits.filtered(lambda t: t.our_role not in ("plaintiff", "complainant", "defendant",
                                                                        "accused"))
            live = subset.filtered(lambda t: t.state in OPEN_STATES)
            side_rows.append({
                "key": key, "title": title, "open": len(live),
                "value": self._ldm_sum_by_currency(live, "matter_value"),
                "opened": len(subset.filtered(lambda t: t.date_opened and date_from <= t.date_opened <= date_to)),
                "closed": len(subset.filtered(lambda t: t.date_closed and date_from <= t.date_closed <= date_to)),
            })

        # Matters opened and closed by kind.
        kinds = dict(Task._fields["kind"]._description_selection(self.env))
        opened = {k: n for k, n in Task._read_group(within("date_opened"), ["kind"], ["__count"])}
        closed = {k: n for k, n in Task._read_group(within("date_closed"), ["kind"], ["__count"])}
        still_open = {k: n for k, n in Task._read_group([("state", "in", OPEN_STATES)], ["kind"], ["__count"])}
        kind_rows = [{"title": kinds[k], "opened": opened.get(k, 0), "closed": closed.get(k, 0),
                      "open": still_open.get(k, 0)}
                     for k in kinds if opened.get(k) or closed.get(k) or still_open.get(k)]

        # Sessions, judgments, challenges, missed clocks.
        Hearing, Judgment, Deadline = self.env["legal.hearing"], self.env["legal.judgment"], self.env["legal.deadline"]
        held = Hearing.search_count(within("date") & Domain("state", "=", "held"))
        planned = Hearing.search_count(within("date") & Domain("state", "=", "planned"))
        judgments = Judgment.search(within("date"))
        results = dict(Judgment._fields["result"]._description_selection(self.env))
        judgment_rows = []
        for result_key, title in list(results.items()) + [(False, _("Not recorded"))]:
            subset = judgments.filtered(lambda j, r=result_key: (j.result or False) == r)
            if subset:
                judgment_rows.append({"title": title, "count": len(subset),
                                      "awarded": self._ldm_sum_by_currency(subset, "amount_awarded")})
        challenges = Deadline.search([("kind", "=", "appeal"), ("state", "in", ("open", "awaiting_service"))],
                                     order="date_safe")
        missed = Deadline.search([("state", "=", "missed"), "|", ("date_deadline", "=", False),
                                  "&", ("date_deadline", ">=", date_from), ("date_deadline", "<=", date_to)],
                                 order="date_deadline")

        # Government transactions by body.
        government = Task.search([("kind", "=", "government")])
        body_rows = []
        for body, tasks in self._group(government, "department_id"):
            row = {
                "title": body.name if body else _("No body set"),
                "opened": len(tasks.filtered(lambda t: t.date_opened and date_from <= t.date_opened <= date_to)),
                "closed": len(tasks.filtered(lambda t: t.date_closed and date_from <= t.date_closed <= date_to)),
                "overdue": len(tasks.filtered(lambda t: t.state in OPEN_STATES and t.due_date and t.due_date < today)),
                "open": len(tasks.filtered(lambda t: t.state in OPEN_STATES)),
            }
            if any(row[k] for k in ("opened", "closed", "overdue", "open")):
                body_rows.append(row)

        # What expires in the next 60 days.
        horizon = today + timedelta(days=60)
        documents = self.env["legal.company.document"].search(
            [("date_expiry", ">=", today), ("date_expiry", "<=", horizon)], order="date_expiry")
        poas = self.env["legal.poa"].search(
            [("state", "=", "active"), ("date_expiry", ">=", today), ("date_expiry", "<=", horizon)],
            order="date_expiry")

        values = self._ldm_helpers()
        values.update(
            doc_ids=[], doc_model="legal.task", docs=Task, data=data, date_from=date_from, date_to=date_to,
            side_rows=side_rows, kind_rows=kind_rows, held=held, planned=planned, judgment_rows=judgment_rows,
            challenges=challenges, missed=missed, body_rows=body_rows, documents=documents, poas=poas,
            horizon=horizon,
        )
        return values

    @api.model
    def _group(self, records, field_name):
        groups = defaultdict(lambda: records.browse())
        for record in records:
            groups[record[field_name]] |= record
        return sorted(groups.items(), key=lambda item: (item[0].display_name or "") if item[0] else "~")


class ReportRegisterBook(models.AbstractModel):
    """سجل الصادر والوارد: the printed register book for a period."""

    _name = "report.legal_department_management.report_ldm_register_book"
    _table = "ldm_report_register_book"  # the model name is longer than a Postgres identifier
    _inherit = "ldm.report.mixin"
    _description = "Correspondence register book"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        today = fields.Date.context_today(self)
        date_to = fields.Date.to_date(data.get("date_to")) or today
        date_from = fields.Date.to_date(data.get("date_from")) or date_to.replace(month=1, day=1)
        domain = [("state", "!=", "draft"), ("date", ">=", date_from), ("date", "<=", date_to)]
        directions = ["incoming", "outgoing"]
        if data.get("direction") in directions:
            directions = [data["direction"]]
        Letter = self.env["legal.correspondence"]
        books = []
        labels = dict(Letter._fields["direction"]._description_selection(self.env))
        for direction in directions:
            letters = Letter.search(domain + [("direction", "=", direction)], order="date, id")
            books.append({"title": labels[direction], "direction": direction, "letters": letters})
        values = self._ldm_helpers()
        values.update(doc_ids=[], doc_model="legal.correspondence", docs=Letter, data=data, books=books,
                      date_from=date_from, date_to=date_to)
        return values


class ReportOfficialLetter(models.AbstractModel):
    _name = "report.legal_department_management.report_ldm_letter"
    _table = "ldm_report_letter"  # the model name is longer than a Postgres identifier
    _inherit = "ldm.report.mixin"
    _description = "Official letter"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["legal.correspondence"].browse(docids or (data or {}).get("ids") or []).exists()
        values = self._ldm_helpers()
        values.update(doc_ids=docs.ids, doc_model="legal.correspondence", docs=docs, data=data or {})
        return values


class ReportOpinionMemo(models.AbstractModel):
    _name = "report.legal_department_management.report_ldm_opinion_memo"
    _table = "ldm_report_opinion_memo"  # the model name is longer than a Postgres identifier
    _inherit = "ldm.report.mixin"
    _description = "Legal opinion memo"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["legal.task"].browse(docids or (data or {}).get("ids") or []).exists()
        values = self._ldm_helpers()
        values.update(doc_ids=docs.ids, doc_model="legal.task", docs=docs, data=data or {})
        return values

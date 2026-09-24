# -*- coding: utf-8 -*-
"""Search behind the command palette (Ctrl+K, SPEC 5.9).

Arabic names are typed many ways (أ/إ/آ/ا, ة/ه, ى/ي, with or without
diacritics and tatweel, with Arabic-Indic or Latin digits), so matching runs on
a normalised form of both the term and the columns. The match itself is one SQL
query per register over the normalised columns; which of the matches the user
may see is then decided by an ordinary ``search`` as that user, so record rules
apply exactly as they do everywhere else.
"""
import re

from odoo import api, models
from odoo.tools import SQL

# The same letter and digit folding as models/ldm_text.normalize, expressed as a
# Postgres translate() so a column can be folded inside the query.
_FOLD_FROM = "أإآٱةىؤئ" + "٠١٢٣٤٥٦٧٨٩" + "۰۱۲۳۴۵۶۷۸۹"
_FOLD_TO = "ااااهيوي" + "0123456789" + "0123456789"
_FOLD_TABLE = str.maketrans(_FOLD_FROM, _FOLD_TO)
# Diacritics (tashkeel), Quranic marks and the tatweel.
_MARKS = "[ؐ-ًؚ-ٰٟۖ-ۭـ]"
_MARKS_RE = re.compile(_MARKS)


def fold(text):
    """Fold ``text`` like the SQL expression does: lower case, one alef, one
    taa, one yaa, Latin digits, no diacritics. Punctuation is kept, so a matter
    number such as CASE/2026/09/007 still matches as typed."""
    value = _MARKS_RE.sub("", str(text or "").strip().lower())
    return " ".join(value.translate(_FOLD_TABLE).split())


def _folded(column):
    return SQL("regexp_replace(translate(lower(coalesce(%s, '')), %s, %s), %s, '', 'g')",
               column, _FOLD_FROM, _FOLD_TO, _MARKS)


class LegalTask(models.Model):
    _inherit = "legal.task"

    @api.model
    def ldm_palette_search(self, term, limit=8, numbers_only=False):
        """Matters, clients and bodies matching ``term``.

        With ``numbers_only`` (the palette's ``#`` namespace) only numbers are
        searched: the matter number, the court case number, the body's
        reference, receipt numbers of visits and expenses, letter numbers and
        court stage case numbers. An empty ``#`` search lists recent matters."""
        limit = max(1, min(int(limit or 8), 20))
        key = fold(term)
        if not key:
            if numbers_only:
                recent = self.search([("state", "in", ("draft", "in_progress", "pending_docs"))],
                                     order="write_date desc", limit=limit)
                return {"matters": self._ldm_palette_matters(recent, ""), "clients": [], "bodies": []}
            return {"matters": [], "clients": [], "bodies": []}
        if len(key) < 2 and not key.isdigit():
            return {"matters": [], "clients": [], "bodies": []}
        self.env.flush_all()
        pattern = f"%{key}%"
        task_ids = self._ldm_palette_task_ids(pattern, numbers_only, limit * 10)
        tasks = self.search([("id", "in", task_ids)]) if task_ids else self.browse()
        order = {tid: index for index, tid in enumerate(task_ids)}
        tasks = tasks.sorted(lambda t: (self._ldm_palette_rank(t, key), order.get(t.id, 0)))[:limit]
        result = {"matters": self._ldm_palette_matters(tasks, key), "clients": [], "bodies": []}
        if numbers_only:
            return result
        result["clients"] = self._ldm_palette_clients(pattern, limit)
        result["bodies"] = self._ldm_palette_bodies(pattern, limit)
        return result

    # ------------------------------------------------------------------
    def _ldm_palette_task_ids(self, pattern, numbers_only, limit):
        like = SQL("LIKE %s", pattern)
        number_fields = [SQL("t.task_number"), SQL("t.court_case_number"), SQL("t.reference")]
        conditions = [SQL("%s %s", _folded(col), like) for col in number_fields]
        conditions += [
            SQL("EXISTS (SELECT 1 FROM legal_task_step s WHERE s.task_id = t.id AND %s %s)",
                _folded(SQL("s.receipt_number")), like),
            SQL("EXISTS (SELECT 1 FROM legal_task_expense e WHERE e.task_id = t.id AND %s %s)",
                _folded(SQL("e.receipt_number")), like),
            SQL("EXISTS (SELECT 1 FROM legal_correspondence k WHERE k.task_id = t.id AND (%s %s OR %s %s))",
                _folded(SQL("k.number")), like, _folded(SQL("k.sender_ref")), like),
            SQL("EXISTS (SELECT 1 FROM legal_court_stage g WHERE g.task_id = t.id AND %s %s)",
                _folded(SQL("g.case_number")), like),
        ]
        if not numbers_only:
            conditions += [SQL("%s %s", _folded(col), like) for col in (
                SQL("t.name"), SQL("t.opponent_name"), SQL("c.name"), SQL("d.name"))]
            conditions.append(SQL("EXISTS (SELECT 1 FROM legal_task_step s2 WHERE s2.task_id = t.id AND %s %s)",
                                  _folded(SQL("s2.name")), like))
        query = SQL("""
            SELECT t.id
              FROM legal_task t
         LEFT JOIN legal_company c ON c.id = t.legal_company_id
         LEFT JOIN legal_department d ON d.id = t.department_id
             WHERE t.active AND (%s)
          ORDER BY t.write_date DESC
             LIMIT %s
        """, SQL(" OR ").join(conditions), limit)
        self.env.cr.execute(query)
        return [row[0] for row in self.env.cr.fetchall()]

    def _ldm_palette_rank(self, task, key):
        """Exact number first, then numbers that start with the term, then a
        title that contains it, then everything else."""
        number = fold(task.task_number)
        if number == key or fold(task.court_case_number) == key:
            return 0
        if number.startswith(key) or number.endswith(key):
            return 1
        if key in fold(task.name):
            return 2
        return 3

    def _ldm_palette_matters(self, tasks, key):
        rows = []
        for payload, task in zip(tasks.ldm_row_payload(), tasks):
            payload["matched"] = self._ldm_palette_matched(task, key) if key else ""
            rows.append(payload)
        return rows

    def _ldm_palette_matched(self, task, key):
        """The field that matched when it is not already on the row, so the
        palette can say why a matter is listed."""
        shown = fold(" ".join([task.task_number or "", task.name or "", task.legal_company_id.name or "",
                               task.department_id.name or ""]))
        if key in shown:
            return ""
        labels = self._fields
        for field in ("court_case_number", "reference", "opponent_name"):
            if key in fold(task[field]):
                return f"{labels[field]._description_string(self.env)}: {task[field]}"
        for step in task.step_ids:
            if key in fold(step.receipt_number):
                return f"{self.env['legal.task.step']._fields['receipt_number']._description_string(self.env)}: {step.receipt_number}"
            if key in fold(step.name):
                return step.name
        for expense in task.expense_ids:
            if key in fold(expense.receipt_number):
                return f"{self.env['legal.task.expense']._fields['receipt_number']._description_string(self.env)}: {expense.receipt_number}"
        for letter in task.correspondence_ids:
            if key in fold(letter.number) or key in fold(letter.sender_ref):
                return f"{self.env['legal.correspondence']._fields['number']._description_string(self.env)}: {letter.number or letter.sender_ref}"
        for stage in task.court_stage_ids:
            if key in fold(stage.case_number):
                return f"{self.env['legal.court.stage']._fields['case_number']._description_string(self.env)}: {stage.case_number}"
        return ""

    def _ldm_palette_clients(self, pattern, limit):
        like = SQL("LIKE %s", pattern)
        query = SQL("""
            SELECT c.id FROM legal_company c
             WHERE c.active AND (%s %s OR %s %s OR %s %s OR %s %s)
          ORDER BY c.name LIMIT %s
        """, _folded(SQL("c.name")), like, _folded(SQL("c.code")), like,
            _folded(SQL("c.registration_number")), like, _folded(SQL("c.tax_number")), like, limit * 5)
        self.env.cr.execute(query)
        ids = [row[0] for row in self.env.cr.fetchall()]
        clients = self.env["legal.company"].search([("id", "in", ids)], limit=limit) if ids else []
        return [{"id": c.id, "name": c.name, "open": c.pending_tasks_count} for c in clients]

    def _ldm_palette_bodies(self, pattern, limit):
        like = SQL("LIKE %s", pattern)
        query = SQL("""
            SELECT d.id FROM legal_department d
         LEFT JOIN legal_ministry m ON m.id = d.ministry_id
             WHERE d.active AND (%s %s OR %s %s OR %s %s)
          ORDER BY d.name LIMIT %s
        """, _folded(SQL("d.name")), like, _folded(SQL("m.name")), like, _folded(SQL("d.code")), like, limit * 5)
        self.env.cr.execute(query)
        ids = [row[0] for row in self.env.cr.fetchall()]
        Department = self.env["legal.department"]
        if not ids or not Department.has_access("read"):
            return []
        return [{"id": d.id, "name": d.name, "ministry": d.ministry_id.name or ""}
                for d in Department.search([("id", "in", ids)], limit=limit)]


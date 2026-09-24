# -*- coding: utf-8 -*-
"""Values for the hearing roll (رول الجلسات) and the substitution letter
(كتاب إنابة). Records are read as the printing user, so record rules apply."""
from odoo import _, api, fields, models
from odoo.tools import format_date


def _time_label(value):
    if not value:
        return ""
    hours, minutes = divmod(round(value * 60), 60)
    return f"{int(hours):02d}:{int(minutes):02d}"


class ReportLdmHearingRoll(models.AbstractModel):
    _name = "report.legal_department_management.report_ldm_hearing_roll"
    _description = "Hearing roll"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        Hearing = self.env["legal.hearing"]
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        if date_from and date_to:
            domain = [("date", ">=", date_from), ("date", "<=", date_to), ("state", "!=", "cancelled")]
            if not data.get("include_held"):
                domain.append(("state", "=", "planned"))
            if data.get("user_ids"):
                domain.append(("attending_user_id", "in", data["user_ids"]))
            if data.get("department_ids"):
                domain.append(("department_id", "in", data["department_ids"]))
            hearings = Hearing.search(domain)
        else:
            hearings = Hearing.browse(docids).exists()
            dates = hearings.mapped("date")
            date_from = min(dates) if dates else False
            date_to = max(dates) if dates else False
        hearings = hearings.sorted(lambda h: (h.department_id.name or "", h.attending_user_id.name or "",
                                              h.date, h.time, h.id))
        groups = []
        for hearing in hearings:
            court = hearing.department_id
            if not groups or groups[-1]["court"] != court:
                groups.append({"court": court, "court_name": court.name or _("Court not set"), "lawyers": []})
            lawyers = groups[-1]["lawyers"]
            person = hearing.attending_user_id
            if not lawyers or lawyers[-1]["user"] != person:
                lawyers.append({"user": person, "name": person.name or _("Nobody assigned"), "rows": []})
            lawyers[-1]["rows"].append(self._ldm_row(hearing))
        return {
            "doc_ids": hearings.ids,
            "doc_model": "legal.hearing",
            "docs": hearings,
            "groups": groups,
            "count": len(hearings),
            "period": self._ldm_period(date_from, date_to),
            "printed_on": format_date(self.env, fields.Date.context_today(self)),
        }

    @api.model
    def _ldm_period(self, date_from, date_to):
        if not date_from:
            return ""
        start, end = fields.Date.to_date(date_from), fields.Date.to_date(date_to)
        if start == end:
            return format_date(self.env, start, date_format="EEEE d MMMM y")
        return _("%(start)s to %(end)s", start=format_date(self.env, start, date_format="EEEE d MMMM y"),
                 end=format_date(self.env, end, date_format="EEEE d MMMM y"))

    @api.model
    def _ldm_row(self, hearing):
        task = hearing.task_id
        needed = hearing.previous_hearing_id.needed_before or ""
        return {
            "hearing": hearing,
            "date": format_date(self.env, hearing.date, date_format="EEE d MMM"),
            "time": _time_label(hearing.time),
            "number": task.task_number or "",
            "case": task.court_case_number or "",
            "client": task.legal_company_id.name or "",
            "role": dict(task._fields["our_role"]._description_selection(self.env)).get(task.our_role, ""),
            "opponent": task.opponent_name or "",
            "purpose": hearing.purpose or "",
            "room": hearing.court_room or "",
            "substitute": hearing.substitute_partner_id.name or "",
            "letter": hearing.needs_substitution_letter,
            "needed": needed,
            "warning": hearing.licence_warning or "",
        }


class ReportLdmSubstitutionLetter(models.AbstractModel):
    _name = "report.legal_department_management.report_ldm_substitution"
    _description = "Substitution letter"

    @api.model
    def _get_report_values(self, docids, data=None):
        hearings = self.env["legal.hearing"].browse(docids).exists()
        letters = []
        for hearing in hearings:
            task = hearing.task_id
            poa = task.poa_id
            principal = poa.agent_user_ids[:1] if poa else task.lawyer_id
            if poa and task.lawyer_id in poa.agent_user_ids:
                principal = task.lawyer_id
            substitute = hearing.substitute_partner_id.name or hearing.attending_user_id.name or ""
            letters.append({
                "hearing": hearing,
                "principal": principal,
                "bar_number": principal.ldm_bar_number or "",
                "substitute": substitute,
                "court": hearing.department_id.name or task.department_id.name or "",
                "today": format_date(self.env, fields.Date.context_today(self)),
                "body": self._ldm_body(hearing, principal, substitute),
            })
        return {"doc_ids": hearings.ids, "doc_model": "legal.hearing", "docs": hearings, "letters": letters}

    @api.model
    def _ldm_body(self, hearing, principal, substitute):
        """The letter as whole sentences, so that each language reads naturally."""
        task = hearing.task_id
        poa = task.poa_id
        values = {
            "principal": principal.name or "",
            "client": task.legal_company_id.name or "",
            "substitute": substitute,
            "date": format_date(self.env, hearing.date, date_format="EEEE d MMMM y"),
            "case": task.court_case_number or task.task_number or "",
            "opponent": task.opponent_name or "",
        }
        if poa:
            values.update(number=poa.number or "", notary=poa.notary_office or "",
                          issued=format_date(self.env, poa.date_issued) if poa.date_issued else "")
            first = _("I, the undersigned lawyer %(principal)s, agent for %(client)s under power of attorney "
                      "no. %(number)s issued by %(notary)s on %(issued)s,", **values)
        else:
            first = _("I, the undersigned lawyer %(principal)s, acting for %(client)s,", **values)
        if values["opponent"]:
            second = _("authorise %(substitute)s to attend on my behalf the court session of %(date)s in case "
                       "no. %(case)s against %(opponent)s, and to take the steps that session requires.", **values)
        else:
            second = _("authorise %(substitute)s to attend on my behalf the court session of %(date)s in case "
                       "no. %(case)s, and to take the steps that session requires.", **values)
        return f"{first} {second}"

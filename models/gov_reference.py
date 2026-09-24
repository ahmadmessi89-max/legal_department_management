# -*- coding: utf-8 -*-
"""Loader of the opt-in Iraqi reference library (SPEC 9.2, research 06 B5).

Idempotent: every record is looked up first by its code, then by its
normalised name (hamza, taa marbuta, alef maksura, spacing and diacritics do
not count), and merged into what exists: only empty fields are filled, nothing a
user typed is overwritten, and nothing is created twice. Running it a second
time creates nothing.
"""
from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from . import gov_reference_data as LIB
from .ldm_text import normalize

AR = "ar_001"


class LegalTaskTemplate(models.Model):
    _inherit = "legal.task.template"

    ldm_ref_code = fields.Char(string="Reference code", copy=False, index=True,
                               help="Set by the Iraqi reference library so a second import recognises the type.")


class LegalReferenceLibrary(models.AbstractModel):
    _name = "legal.reference.library"
    _description = "Iraqi reference library"

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    @staticmethod
    def _keys(name):
        return {k for k in (normalize(name), normalize(name, drop_article=True)) if k}

    def _match(self, records, code, names, code_field="code"):
        """The record of ``records`` with this code, else the one whose
        normalised name equals one of ``names``."""
        if code:
            wanted = code.strip().lower()
            for record in records:
                if (record[code_field] or "").strip().lower() == wanted:
                    return record
        keys = set()
        for name in names:
            keys |= self._keys(name)
        for record in records:
            if self._record_keys(record) & keys:
                return record
        return records.browse()

    def _record_keys(self, record):
        """Comparison keys of a record's name in every language it is kept in."""
        names = [record.with_context(lang="en_US").name]
        if record._fields["name"].translate and self.env["res.lang"]._lang_get(AR):
            names.append(record.with_context(lang=AR).name)
        keys = set()
        for name in names:
            keys |= self._keys(name)
        return keys

    def _fill(self, record, values):
        """Write only the values whose field is empty (or still at its default
        for ``body_kind``). Returns True when something was written."""
        todo = {}
        for name, value in values.items():
            if value in (False, None, "", 0):
                continue
            current = record[name]
            field = record._fields[name]
            if field.type == "many2one":
                if not current:
                    todo[name] = value
            elif not current:
                todo[name] = value
        if todo:
            record.write(todo)
        return bool(todo)

    def _set_arabic(self, record, field_name, arabic):
        if not arabic or not self.env["res.lang"]._lang_get(AR):
            return
        current = record.with_context(lang=AR)[field_name]
        english = record.with_context(lang="en_US")[field_name]
        if not current or current == english:
            record.update_field_translations(field_name, {AR: arabic})

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    @api.model
    def ldm_load(self):
        """Load the whole library; returns counts per kind of record."""
        report = {"ministries": [0, 0], "bodies": [0, 0], "courts": [0, 0], "document_types": [0, 0],
                  "services": [0, 0]}
        env = self.with_context(lang="en_US", active_test=False, tracking_disable=True, mail_create_nolog=True).env
        library = self.with_env(env)
        ministries = library._load_ministries(report)
        bodies = library._load_bodies(ministries, report)
        library._load_courts(ministries, bodies, report)
        doc_types = library._load_document_types(report)
        library._load_services(bodies, doc_types, report)
        return report

    def _load_ministries(self, report):
        Ministry = self.env["legal.ministry"]
        existing = Ministry.search([])
        result = {}
        for key, code, name, kind in LIB.MINISTRIES:
            ministry = self._match(existing, code, [name])
            if ministry:
                if ministry.body_kind in (False, "ministry") and kind != "ministry":
                    ministry.body_kind = kind
                self._fill(ministry, {"code": code if not Ministry.search_count([("code", "=ilike", code)]) else False})
                report["ministries"][1] += 1
            else:
                ministry = Ministry.create({"name": name, "code": code, "body_kind": kind})
                existing |= ministry
                report["ministries"][0] += 1
            result[key] = ministry
        return result

    def _merge_body(self, existing, ministry, code, name):
        Department = self.env["legal.department"]
        by_code = self._match(existing, code, [])
        if by_code:
            return by_code
        keys = self._keys(name)
        same_ministry = existing.filtered(lambda d: d.ministry_id == ministry and self._keys(d.name) & keys)
        if same_ministry:
            return same_ministry[:1]
        anywhere = existing.filtered(lambda d: self._keys(d.name) & keys)
        if len(anywhere) == 1:
            return anywhere
        return Department.browse()

    def _load_bodies(self, ministries, report):
        Department = self.env["legal.department"]
        existing = Department.search([])
        result = {}
        for key, ministry_key, code, name, kind, extra in LIB.BODIES:
            ministry = ministries[ministry_key]
            body = self._merge_body(existing, ministry, code, name)
            if body:
                values = dict(extra, ministry_id=ministry.id,
                              code=code if not Department.search_count([("code", "=ilike", code)]) else False)
                if body.body_kind == "government" and kind != "government":
                    body.body_kind = kind
                self._fill(body, values)
                report["bodies"][1] += 1
            else:
                body = Department.create(dict(extra, name=name, code=code, ministry_id=ministry.id, body_kind=kind))
                existing |= body
                report["bodies"][0] += 1
            result[key] = body
        return result

    def _load_courts(self, ministries, bodies, report):
        Department = self.env["legal.department"]
        existing = Department.search([])
        for key, ministry_key, code, name, kind, degree, parent_key in LIB.COURTS:
            ministry = ministries[ministry_key]
            parent = bodies.get(parent_key) if parent_key else Department.browse()
            court = self._merge_body(existing, ministry, code, name)
            if court:
                if court.body_kind == "government":
                    court.body_kind = kind
                values = {"ministry_id": ministry.id, "court_degree": degree, "governorate": "baghdad",
                          "parent_id": parent.id if parent and parent != court else False,
                          "code": code if not Department.search_count([("code", "=ilike", code)]) else False}
                self._fill(court, values)
                report["courts"][1] += 1
            else:
                court = Department.create({
                    "name": name, "code": code, "ministry_id": ministry.id, "body_kind": kind,
                    "court_degree": degree, "governorate": "baghdad", "parent_id": parent.id or False,
                    "working_hours": LIB.COURT_HOURS,
                })
                existing |= court
                report["courts"][0] += 1
            bodies[key] = court

    def _load_document_types(self, report):
        DocType = self.env["legal.document.type"]
        existing = DocType.search([])
        result = {}
        for code, english, arabic, category, validity, days in LIB.DOCUMENT_TYPES:
            doc_type = self._match(existing, code, [english, arabic])
            if doc_type:
                self._fill(doc_type, {"code": code if not DocType.search_count([("code", "=ilike", code)]) else False,
                                      "validity_days": days})
                report["document_types"][1] += 1
            else:
                doc_type = DocType.create({"name": english, "code": code, "category": category,
                                           "validity": validity, "validity_days": days})
                existing |= doc_type
                report["document_types"][0] += 1
            self._set_arabic(doc_type, "name", arabic)
            result[code] = doc_type
        return result

    def _load_services(self, bodies, doc_types, report):
        Template = self.env["legal.task.template"]
        existing = Template.search([])
        for sequence, (code, body_key, english, arabic, duration, coverage, steps, documents) in enumerate(
                LIB.SERVICES, start=100):
            template = self._match(existing, code, [english, arabic], code_field="ldm_ref_code")
            body = bodies[body_key]
            if template:
                self._fill(template, {"ldm_ref_code": code, "department_id": body.id})
                report["services"][1] += 1
                continue
            template = Template.create({
                "name": english, "ldm_ref_code": code, "kind": "government", "department_id": body.id,
                "duration_days": duration, "track_coverage": coverage,
                "sequence": sequence,
            })
            self._set_arabic(template, "name", arabic)
            for index, step in enumerate(steps, start=1):
                line = self.env["legal.task.template.step"].create({
                    "template_id": template.id, "sequence": index * 10, "name": step["en"],
                    "offset_days": step["offset"], "offset_from": "start" if step["start"] else "previous",
                    "is_visit": step["visit"], "responsible": "responsible",
                })
                self._set_arabic(line, "name", step["ar"])
            for index, (doc_code, mandatory) in enumerate(documents, start=1):
                self.env["legal.task.template.document"].create({
                    "template_id": template.id, "sequence": index * 10,
                    "document_type_id": doc_types[doc_code].id, "mandatory": mandatory,
                })
            existing |= template
            report["services"][0] += 1


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def action_ldm_load_reference_data(self):
        """Load the Iraqi reference library (bodies, courts, document types and
        one government-transaction type per service) and say what changed."""
        user = self.env.user
        if not (user.has_group("base.group_system") or user.has_group("legal_department_management.group_legal_manager")):
            raise AccessError(_("Only a legal manager can load the reference library."))
        report = self.env["legal.reference.library"].sudo().ldm_load()
        created = sum(v[0] for v in report.values())
        message = _(
            "Added %(ministries)s ministries and authorities, %(bodies)s government bodies, %(courts)s courts, "
            "%(types)s document types and %(services)s government services. "
            "Already there and kept: %(old)s records.",
            ministries=report["ministries"][0], bodies=report["bodies"][0], courts=report["courts"][0],
            types=report["document_types"][0], services=report["services"][0],
            old=sum(v[1] for v in report.values()))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Iraqi reference library loaded") if created else _("The reference library was already loaded"),
                "message": message,
                "type": "success" if created else "info",
                "sticky": True,
            },
        }

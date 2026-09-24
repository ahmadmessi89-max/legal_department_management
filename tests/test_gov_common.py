# -*- coding: utf-8 -*-
"""Shared fixtures of the gov stream's tests (no tests of its own)."""
from odoo import fields

from .common import M, LdmCase

# A 1x1 PNG, enough for an image field and an attachment.
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


class GovCase(LdmCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.tax_body = env["legal.department"].create({
            "name": "LDM Test Tax Commission", "ministry_id": cls.ministry.id, "target_days": 5})
        cls.dt_card = env.ref(f"{M}.ldm_doctype_tax_card")
        cls.dt_clearance = env.ref(f"{M}.ldm_doctype_tax_clearance")
        cls.dt_accounts = env.ref(f"{M}.ldm_doctype_final_accounts")
        cls.dt_chamber = env.ref(f"{M}.ldm_doctype_chamber_id")
        cls.t_service = env["legal.task.template"].create({
            "name": "LDM Test Tax clearance",
            "kind": "government",
            "department_id": cls.tax_body.id,
            "duration_days": 10,
            "step_ids": [
                (0, 0, {"sequence": 10, "name": "Collect the documents", "offset_days": 1, "offset_from": "start"}),
                (0, 0, {"sequence": 20, "name": "Submit the request", "offset_days": 1, "is_visit": True}),
                (0, 0, {"sequence": 30, "name": "Collect the letter", "offset_days": 3, "is_visit": True}),
            ],
            "document_ids": [
                (0, 0, {"sequence": 10, "document_type_id": cls.dt_card.id, "mandatory": True}),
                (0, 0, {"sequence": 20, "document_type_id": cls.dt_clearance.id, "mandatory": True}),
                (0, 0, {"sequence": 30, "document_type_id": cls.dt_accounts.id, "mandatory": False}),
            ],
        })
        cls.today = fields.Date.context_today(cls.env["legal.task"])

    def gov_matter(self, client=None, with_clerk=True):
        """A government matter opened by the client's lawyer, with the clerk on its team."""
        client = client or self.client_a
        task_id = self.env["legal.task"].with_user(client.lawyer_id).create_from_template(
            {"template_id": self.t_service.id, "legal_company_id": client.id})
        task = self.env["legal.task"].browse(task_id)
        if with_clerk:
            task.with_user(client.lawyer_id).write({"lawyer_ids": [(4, self.clerk.id)]})
        return task

    def vault_doc(self, doc_type, expiry=None, client=None, **values):
        vals = {"legal_company_id": (client or self.client_a).id, "document_type_id": doc_type.id,
                "number": "N-1", "date_expiry": expiry}
        vals.update(values)
        return self.env["legal.company.document"].create(vals)

# -*- coding: utf-8 -*-
from .common import M, LdmCase


class LitCase(LdmCase):
    """Courts of each degree and a lawsuit for the litigation tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Department = cls.env["legal.department"]

        def court(name, degree, parent=None):
            return Department.create({"name": name, "ministry_id": cls.council.id, "body_kind": "court",
                                      "court_degree": degree, "parent_id": parent.id if parent else False})

        cls.cassation_court = court("LDM Test Cassation Court", "cassation")
        cls.appeal_court = court("LDM Test Appeal Court", "appeal", cls.cassation_court)
        cls.court.parent_id = cls.appeal_court
        cls.final_court = court("LDM Test First Instance Court (final)", "first_instance_final", cls.appeal_court)
        cls.felony_court = court("LDM Test Felony Court", "felony", cls.cassation_court)
        cls.labour_court = court("LDM Test Labour Court", "labour", cls.appeal_court)
        cls.execution_office = Department.create({"name": "LDM Test Execution Directorate", "body_kind": "execution",
                                                  "court_degree": "execution"})
        cls.lawsuit = cls.make_matter(name="Rafidain v. Tigris", template_id=cls.t_lawsuit.id,
                                      department_id=cls.court.id, our_role="plaintiff")

    @classmethod
    def rule(cls, name):
        return cls.env.ref(f"{M}.ldm_rule_{name}")

    def judgment(self, matter=None, **values):
        vals = {"task_id": (matter or self.lawsuit).id, "date": self.d("2026-09-20"),
                "department_id": self.court.id, "court_degree": "first_instance", "law": "civil"}
        vals.update(values)
        return self.env["legal.judgment"].create(vals)

    def hearing(self, matter=None, **values):
        vals = {"task_id": (matter or self.lawsuit).id, "date": self.d("2026-10-01"),
                "department_id": self.court.id, "attending_user_id": self.lawyer.id}
        vals.update(values)
        return self.env["legal.hearing"].create(vals)

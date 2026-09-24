# -*- coding: utf-8 -*-
from odoo.tests import tagged

from ..models.ws_palette import fold
from .ws_common import WsCase


@tagged("post_install", "-at_install", "ldm")
class TestWsPalette(WsCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client_ar = cls.env["legal.company"].create({
            "name": "شركة أحمد الرافدين للتجارة", "lawyer_id": cls.lawyer.id,
            "lawyer_ids": [(6, 0, [cls.lawyer.id])]})
        cls.matter = cls.open_matter(client=cls.client_ar, name="دعوى مطالبة بقيمة البضاعة",
                                     court_case_number="1834/ب/2026", department_id=cls.court.id)
        cls.step(cls.matter, "تسجيل الدعوى", 0, receipt_number="و/88213")
        cls.env["legal.task.expense"].create({"task_id": cls.matter.id, "name": "رسم", "amount": 1000,
                                              "receipt_number": "EXP-7781"})
        cls.hidden = cls.open_matter(client=cls.client_b, name="دعوى الفريق الآخر المحظورة")

    def search(self, user, term, **kw):
        self.env.invalidate_all()
        return self.env["legal.task"].with_user(user).ldm_palette_search(term, **kw)

    def ids(self, result):
        return [row["id"] for row in result["matters"]]

    def test_fold_matches_the_module_normaliser(self):
        self.assertEqual(fold("أحمد"), fold("احمد"))
        self.assertEqual(fold("شركة"), fold("شركه"))
        self.assertEqual(fold("مصطفى"), fold("مصطفي"))
        self.assertEqual(fold("٢٠٢٦"), "2026")
        self.assertEqual(fold("مُحَمَّد"), fold("محمد"))
        self.assertEqual(fold("CASE/2026/09"), "case/2026/09")

    def test_arabic_variants(self):
        for term in ("احمد", "أحمد", "شركه احمد", "الرافدين"):
            self.assertIn(self.matter.id, self.ids(self.search(self.lawyer, term)), term)
        # The client itself is found too, with its open matters.
        clients = self.search(self.lawyer, "احمد الرافدين")["clients"]
        self.assertEqual([c["id"] for c in clients], [self.client_ar.id])
        # Arabic-Indic digits find Latin ones.
        self.assertIn(self.matter.id, self.ids(self.search(self.lawyer, "١٨٣٤")))

    def test_numbers_and_why_a_row_matched(self):
        result = self.search(self.lawyer, "88213")
        row = next(row for row in result["matters"] if row["id"] == self.matter.id)
        self.assertIn("88213", row["matched"])
        numbers = self.search(self.lawyer, "EXP-7781", numbers_only=True)
        self.assertEqual(self.ids(numbers), [self.matter.id])
        self.assertEqual(numbers["clients"], [])
        # A title word is not a number.
        self.assertNotIn(self.matter.id, self.ids(self.search(self.lawyer, "البضاعة", numbers_only=True)))
        # The matter number itself ranks first.
        number = self.search(self.lawyer, self.matter.task_number)
        self.assertEqual(self.ids(number)[0], self.matter.id)

    def test_record_rules_apply(self):
        self.assertNotIn(self.hidden.id, self.ids(self.search(self.lawyer, "المحظورة")))
        self.assertIn(self.hidden.id, self.ids(self.search(self.manager, "المحظورة")))
        self.assertIn(self.hidden.id, self.ids(self.search(self.lawyer2, "المحظورة")))

    def test_bodies_found_by_ministry(self):
        bodies = self.search(self.lawyer, "Judicial Council")["bodies"]
        self.assertIn(self.court.id, [b["id"] for b in bodies])

    def test_short_and_empty_terms(self):
        self.assertEqual(self.search(self.lawyer, "a")["matters"], [])
        recent = self.search(self.lawyer, "", numbers_only=True)
        self.assertTrue(recent["matters"])
        self.assertLessEqual(len(recent["matters"]), 8)

# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from ..models.reg_render import placeholder_values
from .common import M
from .reg_case import RegCase


@tagged("post_install", "-at_install", "ldm")
class TestRegCorrespondence(RegCase):

    def letter(self, user=None, **values):
        vals = {"name": "Letter", "direction": "outgoing", "date": self.d("2031-03-01")}
        vals.update(values)
        return self.Letter.with_user(user or self.clerk).create(vals)

    def test_numbering_continues_per_direction_and_year(self):
        out1 = self.letter(name="First")
        out2 = self.letter(name="Second", date=self.d("2031-03-02"))
        in1 = self.letter(name="From the ministry", direction="incoming", date=self.d("2031-03-02"))
        out_next_year = self.letter(name="Next year", date=self.d("2032-01-05"))
        for letter in (out1, out2, in1, out_next_year):
            letter.action_register()
        self.assertEqual(out1.number, "2031/1")
        self.assertEqual(out2.number, "2031/2")
        self.assertEqual(in1.number, "2031/1")
        self.assertEqual(out_next_year.number, "2032/1")
        self.assertEqual(out1.state, "registered")
        self.assertTrue(in1.received_date)
        self.assertIn("2031/1", out1.display_name)

    def test_typed_number_is_kept_and_the_book_continues_after_it(self):
        typed = self.letter(number="2033/57", date=self.d("2033-02-01"))
        typed.action_register()
        self.assertEqual(typed.number, "2033/57")
        following = self.letter(date=self.d("2033-02-02"))
        following.action_register()
        self.assertEqual(following.number, "2033/58")
        clash = self.letter(number="2033/57", date=self.d("2033-02-03"))
        with self.assertRaises(UserError):
            clash.action_register()

    def test_registered_letter_is_locked(self):
        letter = self.letter()
        letter.write({"number": "draft number is editable"})
        letter.write({"number": False})
        letter.action_register()
        with self.assertRaises(AccessError):
            letter.write({"number": "2031/999"})
        with self.assertRaises(AccessError):
            letter.write({"date": self.d("2031-04-01")})
        with self.assertRaises(AccessError):
            letter.write({"direction": "incoming"})
        # A form saved again sends unchanged values back: that is not a change.
        letter.write({"number": letter.number, "date": letter.date, "name": "Corrected subject"})
        self.assertEqual(letter.name, "Corrected subject")

    def test_status_moves_only_through_the_register(self):
        letter = self.letter()
        with self.assertRaises(AccessError):
            letter.write({"state": "registered"})
        created = self.Letter.with_user(self.clerk).create({"name": "x", "state": "registered"})
        self.assertEqual(created.state, "draft")

    def test_void_not_delete(self):
        draft = self.letter()
        draft.with_user(self.manager).unlink()
        letter = self.letter()
        letter.action_register()
        with self.assertRaises(UserError):
            letter.with_user(self.manager).unlink()
        action = letter.action_ldm_void()
        Wizard = self.env["legal.correspondence.void.wizard"].with_user(self.clerk).with_context(action["context"])
        defaults = Wizard.default_get(["correspondence_id", "reason"])
        self.assertEqual(defaults["correspondence_id"], letter.id)
        self.assertEqual(Wizard.new(defaults).correspondence_id, letter)
        with self.assertRaises(UserError):
            Wizard.create({"reason": "  "}).action_confirm()
        Wizard.create({"reason": "Sent to the wrong directorate"}).action_confirm()
        self.assertEqual(letter.state, "void")
        self.assertEqual(letter.void_reason, "Sent to the wrong directorate")
        self.assertEqual(letter.number, "2031/1")
        with self.assertRaises(UserError):
            letter.with_user(self.manager).unlink()

    def test_reply_due_counts_working_days_and_becomes_a_deadline(self):
        # Received Thursday 1 October 2026; three working days: Sun 4, Mon 5, Tue 6.
        letter = self.letter(direction="incoming", date=self.d("2026-10-01"), received_date=self.d("2026-10-01"),
                             reply_days=3, assigned_user_id=self.lawyer.id)
        self.assertEqual(letter.reply_due_date, self.d("2026-10-06"))
        letter.action_register()
        deadline = self.env["legal.deadline"].search([("source_model", "=", "legal.correspondence"),
                                                      ("source_id", "=", letter.id)])
        self.assertEqual(len(deadline), 1)
        self.assertEqual(deadline.kind, "reply")
        self.assertEqual(deadline.date_safe, self.d("2026-10-06"))
        self.assertEqual(deadline.user_id, self.lawyer)
        self.assertEqual(letter.reply_state, "overdue" if letter.reply_due_date < letter.date.today() else "waiting")
        # Our answer, once registered, closes the clock.
        answer = self.letter(name="Our answer", date=self.d("2026-10-05"), reply_to_id=letter.id)
        answer.action_register()
        self.assertTrue(letter.reply_done)
        self.assertEqual(letter.reply_state, "answered")
        self.assertEqual(deadline.state, "done")

    def test_instruction_due_is_a_deadline_on_the_matter(self):
        matter = self.make_matter()
        letter = self.letter(direction="incoming", date=self.d("2026-10-01"), task_id=matter.id,
                             received_date=self.d("2026-10-01"), referral_note="Prepare the answer",
                             instruction_days=2)
        self.assertEqual(letter.instruction_due, self.d("2026-10-05"))
        self.assertEqual(letter.legal_company_id, matter.legal_company_id)
        letter.action_register()
        deadline = matter.deadline_ids.filtered(lambda d: d.kind == "custom")
        self.assertEqual(len(deadline), 1)
        self.assertEqual(deadline.date_safe, self.d("2026-10-05"))
        letter.action_ldm_void()
        letter._ldm_void("Duplicate")
        self.assertEqual(deadline.state, "cancelled")

    def test_register_needs_the_switch(self):
        self.env["res.config.settings"]._ldm_apply_preset("office")
        letter = self.letter()
        with self.assertRaises(UserError):
            letter.action_register()

    def test_open_matter_from_letter(self):
        letter = self.letter(direction="incoming", name="Tax clearance request", legal_company_id=self.client_a.id,
                             department_id=self.registry_body.id, date=self.d("2031-05-01"))
        letter.action_register()
        action = letter.action_ldm_open_matter()
        Wizard = self.env["legal.reg.matter.wizard"].with_user(self.lawyer).with_context(action["context"])
        fields_list = ["correspondence_id", "legal_company_id", "department_id", "name", "template_id", "key_date",
                       "lawyer_id"]
        defaults = Wizard.default_get(fields_list)
        self.assertEqual(defaults["legal_company_id"], self.client_a.id)
        self.assertEqual(defaults["department_id"], self.registry_body.id)
        self.assertEqual(defaults["name"], "Tax clearance request")
        new = Wizard.new(defaults)
        self.assertEqual(new.correspondence_id, letter)
        self.assertEqual(new.legal_company_id, self.client_a)
        wizard = Wizard.create({"template_id": self.t_government.id})
        result = wizard.action_create()
        matter = self.env["legal.task"].browse(result["res_id"])
        self.assertEqual(letter.task_id, matter)
        self.assertEqual(matter.legal_company_id, self.client_a)
        self.assertEqual(matter.department_id, self.registry_body)
        self.assertTrue(matter.step_ids)
        with self.assertRaises(UserError):
            letter.action_ldm_open_matter()

    def test_document_from_template_in_every_mode(self):
        self.env["res.config.settings"]._ldm_apply_preset("office")
        matter = self.make_matter(department_id=self.registry_body.id)
        action = matter.with_user(self.lawyer).action_ldm_new_document()
        Wizard = self.env["legal.document.wizard"].with_user(self.lawyer).with_context(action["context"])
        defaults = Wizard.default_get(["task_id", "department_id", "lang", "signatory_id"])
        self.assertEqual(defaults["task_id"], matter.id)
        self.assertEqual(defaults["department_id"], self.registry_body.id)
        wizard = Wizard.new(dict(defaults, template_id=self.env.ref(f"{M}.ldm_letter_to_body").id, lang="en_US"))
        wizard._onchange_render()
        self.assertIn(matter.task_number, wizard.body_html)
        wizard = Wizard.create({"template_id": self.env.ref(f"{M}.ldm_letter_to_body").id, "lang": "en_US"})
        wizard._onchange_render()
        result = wizard.action_create()
        letter = self.Letter.browse(result["res_id"])
        self.assertEqual(letter.state, "draft")
        self.assertEqual(letter.direction, "outgoing")
        self.assertEqual(letter.task_id, matter)
        self.assertIn(matter.task_number, letter.body_html)
        filed = matter.attachment_ids.filtered(lambda a: a.res_model == "legal.task" and a.res_id == matter.id)
        self.assertEqual(len(filed), 1)
        self.assertEqual(letter.attachment_ids, filed)

    def arabic_installed(self):
        return "ar_001" in dict(self.env["res.lang"].get_installed())

    def test_seed_translations_fill_only_what_is_missing(self):
        if not self.arabic_installed():
            self.skipTest("Arabic is not installed in this database")
        Template = self.env["legal.letter.template"]
        xmlid = f"{M}.ldm_letter_general_request"
        template = self.env.ref(xmlid)
        # Installed by the module data: the Arabic text is there.
        self.assertNotEqual(template.with_context(lang="ar_001").body, template.with_context(lang="en_US").body)
        # A text the manager rewrote survives an upgrade.
        template.update_field_translations("name", {"ar_001": "Rewritten by the manager"})
        Template._ldm_seed_translations(xmlid, {"name": {"ar_001": "Shipped", "xx_XX": "ignored"}})
        self.assertEqual(template.with_context(lang="ar_001").name, "Rewritten by the manager")
        # A missing translation is filled.
        template.update_field_translations("name", {"ar_001": False})
        Template._ldm_seed_translations(xmlid, {"name": {"ar_001": "Shipped"}})
        self.assertEqual(template.with_context(lang="ar_001").name, "Shipped")
        self.assertEqual(template.with_context(lang="en_US").name, "General request")
        # A seed template somebody deleted is skipped, not an upgrade error.
        self.assertTrue(Template._ldm_seed_translations(f"{M}.ldm_letter_no_such_template", {"name": {"ar_001": "x"}}))

    def test_letter_uses_the_arabic_template_text(self):
        if not self.arabic_installed():
            self.skipTest("Arabic is not installed in this database")
        matter = self.make_matter()
        template = self.env.ref(f"{M}.ldm_letter_to_body")
        values = placeholder_values(self.env, task=matter, lang="ar_001")
        _subject, arabic = template.ldm_render(values, lang="ar_001")
        _subject, english = template.ldm_render(values, lang="en_US")
        self.assertNotEqual(arabic, english)
        self.assertIn(matter.task_number, arabic)

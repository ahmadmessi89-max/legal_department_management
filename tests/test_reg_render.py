# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import tagged

from ..models.reg_render import money, placeholder_values, render_line, render_text
from .common import M
from .reg_case import RegCase


@tagged("post_install", "-at_install", "ldm")
class TestRegRender(RegCase):

    def test_known_placeholders_are_filled_and_escaped(self):
        html = render_text(self.env, "Dear {client},\nsee {matter_number}.", {"client": "<b>A & B</b>", "matter_number": "C/1"})
        self.assertIn("Dear &lt;b&gt;A &amp; B&lt;/b&gt;,<br/>see C/1.", html)
        self.assertTrue(html.startswith("<p>"))

    def test_the_template_text_itself_is_escaped(self):
        html = render_text(self.env, "<script>alert(1)</script> {client}", {"client": "X"})
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_unknown_placeholder_stays_literal(self):
        self.assertIn("{nonexistent}", render_text(self.env, "Hello {nonexistent}", {"client": "X"}))
        self.assertIn("{value:&gt;10}", render_text(self.env, "{value:>10}", {}))
        self.assertEqual(render_line(self.env, "Re {subject} {x}", {"subject": "Visa"}), "Re Visa {x}")

    def test_dotted_and_indexed_placeholders_are_refused(self):
        for text in ("{client.partner_id.email}", "{client[0]}", "{client.__class__}",
                     "{client:{client.__class__}}", "{matter} {0.__globals__}"):
            with self.assertRaises(UserError, msg=text):
                render_text(self.env, text, {"client": "X", "matter": "Y"})
        with self.assertRaises(UserError):
            render_line(self.env, "{subject.upper}", {"subject": "x"})

    def test_conversions_do_not_leak_representations(self):
        self.assertEqual(render_line(self.env, "{client!r}", {"client": "A"}), "A")

    def test_stray_braces_do_not_break_the_letter(self):
        html = render_text(self.env, "Amount { to confirm, client {client}", {"client": "Rafidain"})
        self.assertIn("Rafidain", html)
        self.assertIn("{ to confirm", html)
        with self.assertRaises(UserError):
            render_text(self.env, "{ stray {client.name}", {"client": "X"})

    def test_values_for_a_matter(self):
        matter = self.make_matter(court_case_number="1234/b/2026", department_id=self.court.id)
        values = placeholder_values(self.env, task=matter)
        self.assertEqual(values["client"], "LDM Client A")
        self.assertEqual(values["matter_number"], matter.task_number)
        self.assertEqual(values["court_case_number"], "1234/b/2026")
        self.assertEqual(values["body"], self.court.name)
        self.assertEqual(values["responsible"], self.lawyer.name)
        self.assertTrue(values["today"])

    def test_seed_template_renders_for_a_matter(self):
        matter = self.make_matter()
        template = self.env.ref(f"{M}.ldm_letter_to_body")
        subject, body = template.ldm_render(placeholder_values(self.env, task=matter), lang="en_US")
        self.assertEqual(subject, matter.name)
        self.assertIn(matter.task_number, body)
        self.assertIn("LDM Client A", body)

    def test_money_in_whole_dinars(self):
        iqd = self.env.ref("base.IQD")
        self.assertNotIn(".", money(self.env, 1250000.4, iqd).replace(iqd.symbol, ""))
        usd = self.env.ref("base.USD")
        self.assertIn(".50", money(self.env, 12.5, usd))

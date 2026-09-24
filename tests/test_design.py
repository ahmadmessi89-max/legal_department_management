# -*- coding: utf-8 -*-
"""The design pass: the shared view identity, reminders that read as people
write, the company file's service overview and the managers' analytics board."""
import base64
from datetime import timedelta

from lxml import etree

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools.misc import format_date

from .common import M, LdmCase
from .test_gov_common import GovCase
from . import test_design_analytics  # noqa: F401


@tagged("post_install", "-at_install", "ldm")
class TestDesignViews(LdmCase):

    def test_every_native_view_carries_the_identity(self):
        """Every list, kanban, form, pivot and graph of the module publishes the
        tokens through o_ldm_view; calendars through the ldm_calendar js_class."""
        views = self.env["ir.ui.view"].search([
            ("model", "like", "legal."), ("inherit_id", "=", False),
            ("type", "in", ("form", "list", "kanban", "pivot", "graph", "calendar"))])
        module_views = views.filtered(lambda v: (v.get_external_id().get(v.id) or "").startswith(M + "."))
        self.assertGreater(len(module_views), 50)
        for view in module_views:
            root = etree.fromstring(view.arch_db)
            if view.type == "calendar":
                self.assertEqual(root.get("js_class"), "ldm_calendar", view.name)
            else:
                self.assertIn("o_ldm_view", (root.get("class") or "").split(), view.name)
        badges = module_views.filtered(lambda v: 'widget="badge"' in v.arch_db)
        self.assertFalse(badges, "Status pills use the ldm_pill widget")

    def test_matter_list_opens_with_six_columns(self):
        arch = self.env["legal.task"].with_user(self.lawyer).get_views([(False, "list")])["views"]["list"]["arch"]
        root = etree.fromstring(arch)
        visible = [f for f in root.iter("field")
                   if f.getparent() is root and f.get("optional") != "hide"
                   and f.get("column_invisible") not in ("1", "True", "true")]
        self.assertLessEqual(len(visible), 6, [f.get("name") for f in visible])

    def test_a_client_monogram_is_the_letter_that_names_it(self):
        Company = self.env["legal.company"]
        cases = {"شركة الرافدين للمقاولات العامة": "ر", "مجموعة دجلة التجارية": "د",
                 "السيد أحمد عبد الكريم": "أ", "شركة نينوى للنقل البري": "ن",
                 "The Babylon Trading Company": "B", "شركة الأمل": "أ"}
        for name, letter in cases.items():
            self.assertEqual(Company.new({"name": name}).ldm_monogram, letter, name)

    def test_a_new_colleague_gets_the_letter_of_their_name(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {"name": "المحامية هدى الكعبي", "login": "ldm_t_huda"})
        self.assertIn(">ه</text>".encode(), base64.b64decode(user.image_1920))
        user.name = "د. كريم الموسوي"
        self.assertIn(">ك</text>".encode(), base64.b64decode(user.image_1920), "a rename redraws the letter")

    def test_stored_letter_avatars_are_redrawn_and_photos_kept(self):
        Users = self.env["res.users"].with_context(no_reset_password=True)
        drawn = Users.create({"name": "المستشار سعد الربيعي", "login": "ldm_t_saad"})
        photo = Users.create({"name": "المحامي علي", "login": "ldm_t_ali"})
        # what Odoo stored for a user created before this version: the title's "ا"
        drawn.image_1920 = base64.b64encode(
            b"<?xml version='1.0' encoding='UTF-8' ?><svg height='180' width='180' "
            b"xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>"
            b"<rect fill='hsl(200, 50%, 45%)' height='180' width='180'/><text fill='#ffffff' font-size='96' "
            b"text-anchor='middle' x='90' y='125' font-family='sans-serif'>" + "ا".encode() + b"</text></svg>")
        png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        photo.image_1920 = png
        self.env["res.users"]._ldm_refresh_letter_avatars()
        self.assertIn(">س</text>".encode(), base64.b64decode(drawn.image_1920))
        self.assertEqual(photo.image_1920.decode() if isinstance(photo.image_1920, bytes) else photo.image_1920, png)

    def test_hearing_time_uses_the_widget_without_midnight(self):
        views = self.env["ir.ui.view"].search([("model", "=", "legal.hearing"), ("type", "in", ("list", "form"))])
        for view in views:
            self.assertNotIn('name="time" widget="float_time"', view.arch_db, view.name)


@tagged("post_install", "-at_install", "ldm")
class TestDesignReminders(LdmCase):

    def setUp(self):
        super().setUp()
        self.today = fields.Date.context_today(self.env["legal.task"].with_context(tz="Asia/Baghdad"))
        self.matter = self.make_matter(state="in_progress", department_id=self.court.id)
        self.hearing = self.env["legal.hearing"].create({
            "task_id": self.matter.id, "date": self.today + timedelta(days=1), "department_id": self.court.id,
            "attending_user_id": self.lawyer.id})
        self.session_type = self.env.ref(f"{M}.ldm_activity_session")

    def session_reminders(self):
        return self.matter.activity_ids.filtered(lambda a: a.activity_type_id == self.session_type)

    def test_summary_reads_the_date_in_the_readers_words(self):
        self.env["legal.task"]._ldm_run_reminders()
        reminder = self.session_reminders()
        self.assertEqual(len(reminder), 1)
        iso = fields.Date.to_string(self.hearing.date)
        self.assertNotIn(iso, reminder.summary)
        readable = format_date(self.env(context=dict(self.env.context, lang=self.lawyer.lang)), self.hearing.date,
                               date_format="d MMMM")
        self.assertIn(readable, reminder.summary)
        self.assertEqual(reminder.ldm_reminder_key, f"legal.hearing,{self.hearing.id}")

    def test_arabic_reader_gets_arabic_month(self):
        if not self.env["res.lang"]._lang_get("ar_001"):
            self.skipTest("Arabic is not installed on this database")
        self.lawyer.lang = "ar_001"
        self.env["legal.task"]._ldm_run_reminders()
        reminder = self.session_reminders()
        arabic = format_date(self.env(context=dict(self.env.context, lang="ar_001")), self.hearing.date,
                             date_format="MMMM")
        self.assertIn(arabic, reminder.summary)
        self.assertNotIn(fields.Date.to_string(self.hearing.date), reminder.summary)

    def test_a_moved_session_keeps_one_reminder_with_the_new_date(self):
        Task = self.env["legal.task"]
        Task._ldm_run_reminders()
        first = self.session_reminders()
        self.hearing.date = self.today + timedelta(days=2)
        Task._ldm_run_reminders()
        Task._ldm_run_reminders()
        reminder = self.session_reminders()
        self.assertEqual(reminder, first, "The same reminder follows the session")
        self.assertEqual(reminder.date_deadline, self.hearing.date)
        self.assertIn(format_date(self.env(context=dict(self.env.context, lang=self.lawyer.lang)),
                                  self.hearing.date, date_format="d MMMM"), reminder.summary)

    def test_a_reminder_written_before_keys_is_adopted_not_duplicated(self):
        legacy = self.matter.activity_schedule(
            activity_type_id=self.session_type.id, user_id=self.lawyer.id, date_deadline=self.hearing.date,
            summary="Court session on %s — %s" % (fields.Date.to_string(self.hearing.date), self.matter.task_number))
        self.env["legal.task"]._ldm_run_reminders()
        reminder = self.session_reminders()
        self.assertEqual(reminder, legacy)
        self.assertEqual(reminder.ldm_reminder_key, f"legal.hearing,{self.hearing.id}")
        self.assertNotIn(fields.Date.to_string(self.hearing.date), reminder.summary)

    def test_recording_the_session_closes_it_by_key_not_by_text(self):
        self.env["legal.task"]._ldm_run_reminders()
        reminder = self.session_reminders()
        reminder.summary = "Something a person rewrote"
        self.hearing.write({"state": "held", "outcome": "pleading"})
        self.assertFalse(self.session_reminders())

    def test_target_date_reminder_is_keyed_on_the_matter(self):
        matter = self.make_matter(state="in_progress", due_date=self.today)
        self.env["legal.task"]._ldm_run_reminders()
        target = matter.activity_ids.filtered(lambda a: a.activity_type_id == self.env.ref(f"{M}.ldm_activity_target"))
        self.assertEqual(target.ldm_reminder_key, f"legal.task,{matter.id}:target")
        matter._ldm_close_reminders("ldm_activity_target", key=f"legal.task,{matter.id}")
        self.assertFalse(target.exists() and target.active)


@tagged("post_install", "-at_install", "ldm")
class TestDesignServiceOverview(GovCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.t_service.track_coverage = True
        cls.t_other = cls.env["legal.task.template"].create({
            "name": "LDM Test Chamber renewal", "kind": "government", "department_id": cls.registry_body.id,
            "track_coverage": True})

    def overview(self, user, client=None):
        return (client or self.client_a).with_user(user).ldm_get_service_overview()

    def service(self, payload, template):
        return next(s for b in payload["bodies"] for s in b["services"] if s["template_id"] == template.id)

    def test_every_tracked_service_is_listed_body_by_body(self):
        payload = self.overview(self.lawyer)
        bodies = {b["id"]: b for b in payload["bodies"]}
        self.assertIn(self.tax_body.id, bodies)
        self.assertIn(self.registry_body.id, bodies)
        row = self.service(payload, self.t_service)
        self.assertEqual(row["state"], "due")
        self.assertTrue(row["can_start"])
        self.assertFalse(row["can_open"])
        tracked = self.env["legal.task.template"].search_count([("track_coverage", "=", True)])
        self.assertEqual(payload["totals"]["total"], tracked, "One row per tracked service, no more")
        for body in payload["bodies"]:
            self.assertEqual(body["total"], len(body["services"]))

    def test_an_open_matter_shows_its_number_and_opens(self):
        matter = self.gov_matter()
        row = self.service(self.overview(self.lawyer), self.t_service)
        self.assertEqual(row["state"], "open")
        self.assertEqual(row["task_id"], matter.id)
        self.assertEqual(row["task_number"], matter.task_number)
        self.assertTrue(row["can_open"])
        self.assertFalse(row["can_start"])
        self.assertEqual(row["responsible"]["id"], matter.lawyer_id.id)

    def test_done_this_year_is_green(self):
        matter = self.gov_matter()
        # Closing goes through the close dialog; the coverage view only reads
        # the stored state and closing date, so they are set directly here.
        self.env.flush_all()
        self.env.cr.execute("UPDATE legal_task SET state = 'done', date_closed = %s WHERE id = %s",
                            [self.today, matter.id])
        self.env.invalidate_all()
        row = self.service(self.overview(self.lawyer), self.t_service)
        self.assertEqual(row["state"], "done")
        self.assertEqual(row["tone"], "success")
        self.assertEqual(row["date_kind"], "done")

    def test_an_obligation_past_its_date_is_overdue(self):
        self.env["legal.obligation"].create({
            "legal_company_id": self.client_a.id, "name": "LDM Test yearly clearance",
            "template_id": self.t_service.id, "recurrence": "yearly",
            "month": 1, "day": 1, "lead_days": 1})
        obligation = self.env["legal.obligation"].search([("name", "=", "LDM Test yearly clearance")])
        obligation.next_date = self.today - timedelta(days=3)
        row = self.service(self.overview(self.lawyer), self.t_service)
        self.assertTrue(row["overdue"])
        self.assertEqual(row["tone"], "danger")

    def test_auditor_reads_and_never_starts(self):
        payload = self.overview(self.auditor)
        self.assertFalse(payload["can_start"])
        self.assertTrue(payload["bodies"])
        self.assertFalse(any(s["can_start"] for b in payload["bodies"] for s in b["services"]))

    def test_a_lawyer_outside_the_clients_team_cannot_read_it(self):
        with self.assertRaises(AccessError):
            self.overview(self.lawyer2)

    def test_the_form_field_carries_the_same_payload(self):
        client = self.client_a.with_user(self.lawyer)
        self.assertEqual(client.read(["ldm_service_overview"])[0]["ldm_service_overview"]["totals"],
                         self.overview(self.lawyer)["totals"])

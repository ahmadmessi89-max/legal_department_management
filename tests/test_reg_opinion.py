# -*- coding: utf-8 -*-
import re

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import M
from .reg_case import RegCase


@tagged("post_install", "-at_install", "ldm")
class TestRegOpinion(RegCase):

    def opinion(self, **values):
        vals = {"template_id": self.env.ref(f"{M}.ldm_template_opinion").id, "state": "in_progress",
                "question": "May the company terminate the lease early?",
                "opinion_html": "<p>Yes, with three months' notice under clause 12.</p>",
                "requesting_unit": "Procurement",
                # The approver who issues it works on it (approvers see what they are given).
                "lawyer_ids": [(6, 0, [self.lawyer.id, self.approver.id])]}
        vals.update(values)
        return self.make_matter(**vals)

    def test_issue_freezes_and_numbers(self):
        matter = self.opinion()
        self.assertEqual(matter.kind, "opinion")
        self.assertFalse(matter.with_user(self.lawyer).ldm_can_issue_opinion)
        self.assertTrue(matter.with_user(self.approver).ldm_can_issue_opinion)
        with self.assertRaises(AccessError):
            matter.with_user(self.lawyer).action_issue_opinion()
        matter.with_user(self.approver).action_issue_opinion()
        year = fields.Date.context_today(matter).year
        self.assertRegex(matter.opinion_number, rf"^{year}/\d+$")
        self.assertEqual(matter.opinion_date, fields.Date.context_today(matter))
        self.assertEqual(matter.opinion_issued_by_id, self.approver)
        self.assertTrue(matter.opinion_memo_id)
        self.assertIn(matter.opinion_memo_id, matter.attachment_ids)
        self.assertFalse(matter.with_user(self.approver).ldm_can_issue_opinion)
        for user in (self.lawyer, self.manager):
            with self.assertRaises(UserError):
                matter.with_user(user).write({"opinion_html": "<p>No.</p>"})
            with self.assertRaises(UserError):
                matter.with_user(user).write({"question": "Changed"})
        with self.assertRaises(AccessError):
            matter.with_user(self.manager).write({"opinion_number": "2026/999"})
        with self.assertRaises(UserError):
            matter.with_user(self.approver).action_issue_opinion()
        # Other fields stay editable.
        matter.with_user(self.lawyer).write({"is_urgent": True})

    def test_numbers_follow_each_other(self):
        first, second = self.opinion(), self.opinion()
        first.with_user(self.approver).action_issue_opinion()
        second.with_user(self.approver).action_issue_opinion()
        one = int(re.search(r"(\d+)$", first.opinion_number).group(1))
        two = int(re.search(r"(\d+)$", second.opinion_number).group(1))
        self.assertEqual(two, one + 1)

    def test_nothing_to_issue(self):
        with self.assertRaises(UserError):
            self.opinion(opinion_html="<p><br></p>").with_user(self.approver).action_issue_opinion()
        with self.assertRaises(UserError):
            self.make_matter(state="in_progress").with_user(self.approver).action_issue_opinion()

    def test_revision_supersedes(self):
        matter = self.opinion()
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).action_ldm_revise_opinion()
        matter.with_user(self.approver).action_issue_opinion()
        result = matter.with_user(self.lawyer).action_ldm_revise_opinion()
        revision = self.env["legal.task"].browse(result["res_id"])
        self.assertEqual(revision.supersedes_id, matter)
        self.assertEqual(matter.superseded_by_id, revision)
        self.assertFalse(revision.opinion_number)
        self.assertEqual(revision.question, matter.question)
        with self.assertRaises(UserError):
            matter.with_user(self.lawyer).action_ldm_revise_opinion()
        revision.with_user(self.lawyer).write({"opinion_html": "<p>Yes, with six months' notice.</p>"})
        revision.write({"state": "in_progress"})
        revision.with_user(self.approver).action_issue_opinion()
        self.assertNotEqual(revision.opinion_number, matter.opinion_number)

    def test_register_search_finds_words(self):
        matter = self.opinion(question="Is the Basra warehouse lease renewable?")
        matter.with_user(self.approver).action_issue_opinion()
        Task = self.env["legal.task"].with_user(self.manager)
        found = Task.search(["|", ("question", "ilike", "warehouse"), ("opinion_html", "ilike", "warehouse")])
        self.assertIn(matter, found)
        found = Task.search([("opinion_html", "ilike", "clause 12"), ("opinion_number", "!=", False)])
        self.assertIn(matter, found)

# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import M, LdmCase


@tagged("post_install", "-at_install", "ldm")
class TestFoundationModes(LdmCase):

    def implied(self, name):
        return self.env.ref(f"{M}.{name}") in self.env.ref("base.group_user").all_implied_ids

    def test_presets_set_the_switches(self):
        Settings = self.env["res.config.settings"]
        Settings._ldm_apply_preset("office")
        self.assertTrue(self.implied("group_ldm_billing"))
        self.assertTrue(self.implied("group_ldm_conflicts"))
        self.assertFalse(self.implied("group_ldm_approvals"))
        self.assertTrue(self.implied("group_ldm_terms_office"))
        self.assertFalse(self.implied("group_ldm_terms_department"))
        self.assertTrue(self.lawyer.has_group(f"{M}.group_ldm_billing"))
        Settings._ldm_apply_preset("department")
        self.assertFalse(self.implied("group_ldm_billing"))
        self.assertTrue(self.implied("group_ldm_approvals"))
        self.assertTrue(self.implied("group_ldm_terms_department"))
        Settings._ldm_apply_preset("hybrid")
        self.assertFalse(self.implied("group_ldm_terms_department"))
        self.assertFalse(self.implied("group_ldm_terms_office"))

    def test_switching_mode_adds_no_required_field(self):
        matter = self.make_matter()
        self.env["res.config.settings"]._ldm_apply_preset("office")
        matter.with_user(self.lawyer).write({"name": "still saves"})
        self.env["legal.task"].with_user(self.lawyer).create({"name": "minimal", "legal_company_id": self.client_a.id})

    def test_mode_never_changes_visibility(self):
        other = self.make_matter(client=self.client_b)
        for preset in ("department", "office", "hybrid", "solo"):
            self.env["res.config.settings"]._ldm_apply_preset(preset)
            if preset == "solo":
                continue  # solo sets "see every non-confidential matter" on purpose
            self.assertNotIn(other, self.env["legal.task"].with_user(self.lawyer).search([]))

    def test_settings_screen_loads(self):
        settings = self.env["res.config.settings"].create({})
        settings.ldm_preset = "office"
        settings._onchange_ldm_preset()
        self.assertTrue(settings.group_ldm_billing)
        settings.execute()
        self.assertTrue(self.implied("group_ldm_billing"))

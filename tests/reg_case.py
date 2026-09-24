# -*- coding: utf-8 -*-
"""Shared set-up for the registers' tests (not a test module itself)."""
from odoo.tests.common import new_test_user

from .common import M, LdmCase


class RegCase(LdmCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The hybrid preset leaves requests off; the registers' tests need them.
        cls.env.ref("base.group_user").sudo()._apply_group(cls.env.ref(f"{M}.group_ldm_requests"))
        cls.requester = new_test_user(cls.env, login="ldm_requester", groups="base.group_user",
                                      name="Plain Employee", tz="Asia/Baghdad")
        cls.requester2 = new_test_user(cls.env, login="ldm_requester2", groups="base.group_user",
                                       name="Other Employee", tz="Asia/Baghdad")
        cls.Letter = cls.env["legal.correspondence"]
        cls.Poa = cls.env["legal.poa"]
        cls.Request = cls.env["legal.request"]
        cls.Report = cls.env["ir.actions.report"]

    @classmethod
    def html(cls, report_name, ids, data=None, user=None):
        Report = cls.env["ir.actions.report"].with_user(user) if user else cls.env["ir.actions.report"]
        content, kind = Report._render_qweb_html(f"{M}.{report_name}", ids, data=data)
        return content.decode() if isinstance(content, bytes) else content

# -*- coding: utf-8 -*-
"""Fixtures for the workspace tests: a few dated items around "today" (in
the users' timezone), on matters of the two lawyers' clients."""
from datetime import timedelta

from odoo import fields

from .common import LdmCase


class WsCase(LdmCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["legal.task"].with_user(cls.lawyer))
        cls.Step = cls.env["legal.task.step"]
        cls.Hearing = cls.env["legal.hearing"]
        cls.Deadline = cls.env["legal.deadline"]

    @classmethod
    def day(cls, offset):
        return cls.today + timedelta(days=offset)

    @classmethod
    def open_matter(cls, client=None, **vals):
        vals.setdefault("state", "in_progress")
        return cls.make_matter(client=client, **vals)

    @classmethod
    def step(cls, task, name, offset, user=None, **vals):
        values = {"task_id": task.id, "name": name, "date_due": cls.day(offset) if offset is not None else False}
        if user:
            values["user_id"] = user.id
        values.update(vals)
        return cls.Step.create(values)

    @staticmethod
    def rows(payload, band=None):
        out = []
        for entry in payload["bands"]:
            if band is None or entry["key"] == band:
                out.extend(entry["rows"])
        return out

    @staticmethod
    def band(payload, key):
        return next(entry for entry in payload["bands"] if entry["key"] == key)

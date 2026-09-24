# -*- coding: utf-8 -*-
"""Reminders that read as people write, and are found again by what they are
about.

The daily run (``legal.task._ldm_run_reminders``) keeps one open activity per
(matter, person, kind, source). Its summary is written in the reminded
person's language with the date as they read it ("Court session on 24
September — CASE/2026/09/218"), so the text changes with the reader and with
the date; the activity therefore carries a stable key naming its source
(``"legal.hearing,12"``, ``"legal.deadline,7"``, ``"legal.task,3:target"``),
and closing a reminder when its source is done matches that key, never the
wording.
"""
from odoo import fields, models
from odoo.tools.misc import format_date


class MailActivity(models.Model):
    _inherit = "mail.activity"

    ldm_reminder_key = fields.Char(
        string="Reminder source", index="btree_not_null", copy=False, readonly=True,
        help="The record a legal reminder is about, so it is closed when that record is done.")


def ldm_key(record, suffix=None):
    """The stable key of a reminder about ``record`` (and one variant of it)."""
    key = f"{record._name},{record.id}"
    return f"{key}:{suffix}" if suffix else key


def ldm_key_matches(value, key):
    """True when an activity's key is ``key`` or one of its variants."""
    return bool(value) and (value == key or value.startswith(key + ":"))


def ldm_reminder_match(activity, key, summary, date):
    """True when ``activity`` is the reminder of this source. A keyed activity
    matches only its key. One written before keys existed (or by a source
    without a key) matches the same text, or, for a keyed source, the same
    day: it is then adopted, its text rewritten and its key set."""
    if activity.ldm_reminder_key:
        return bool(key) and activity.ldm_reminder_key == key
    return activity.summary == summary or (bool(key) and activity.date_deadline == date)


def ldm_day(env, day, today=None):
    """A date as the reader says it, in their language: "24 September", with
    the year only when it is not this year ("3 January 2027")."""
    if not day:
        return ""
    today = today or fields.Date.context_today(env["res.users"])
    return format_date(env, day, date_format="d MMMM" if day.year == today.year else "d MMMM y")

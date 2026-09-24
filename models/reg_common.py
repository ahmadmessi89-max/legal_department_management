# -*- coding: utf-8 -*-
"""Small helpers the registers share: deadlines kept in step with a source
record, reminders on register records, and attaching a rendered report."""
import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def value_of(record, name):
    """A field's value in the shape ``write`` takes it (ids for relations)."""
    value = record[name]
    return value.id if isinstance(value, models.BaseModel) else value


def sync_deadline(record, kind, values, close_state=None):
    """Keep exactly one open ``legal.deadline`` of ``kind`` for ``record``.

    ``values`` (name, dates, user, client, matter...) when the deadline should
    exist; ``None`` when it should not, in which case an open one is moved to
    ``close_state`` (``done`` or ``cancelled``; ``None`` leaves it open for the
    deadline engine to call missed). A deadline somebody already closed for the
    same date is never reopened, so a daily run cannot undo a person's decision.
    Deadlines are bookkeeping, written with sudo: a clerk registering a letter
    may not create deadlines by hand, but the letter's clock must exist.
    """
    Deadline = record.env["legal.deadline"].sudo()
    domain = [("source_model", "=", record._name), ("source_id", "=", record.id), ("kind", "=", kind)]
    existing = Deadline.search(domain + [("state", "=", "open")], order="id")
    if values:
        if existing:
            keep = existing[0]
            changed = {key: value for key, value in values.items() if value_of(keep, key) != value}
            if changed:
                keep.write(changed)
            (existing - keep).write({"state": "cancelled"})
            return keep
        closed = Deadline.search(domain + [("state", "!=", "open"), ("date_safe", "=", values.get("date_safe"))],
                                 limit=1)
        if closed:
            return closed
        return Deadline.create(dict(values, kind=kind, source_model=record._name, source_id=record.id))
    if existing and close_state:
        existing.write({"state": close_state})
    return Deadline.browse()


def ensure_activity(record, user, date, summary, type_xmlid):
    """One open reminder per (record, person, kind, subject); a second run
    moves its date instead of adding another."""
    activity_type = record.env.ref(f"legal_department_management.{type_xmlid}", raise_if_not_found=False)
    existing = record.activity_ids.filtered(
        lambda a: a.user_id == user and a.summary == summary and a.activity_type_id == activity_type)
    if existing:
        if existing[0].date_deadline != date:
            existing[0].sudo().date_deadline = date
        return existing[0]
    return record.sudo().activity_schedule(
        activity_type_id=activity_type.id if activity_type else False,
        summary=summary, user_id=user.id, date_deadline=date)


def close_activities(records, type_xmlid, feedback=None):
    activity_type = records.env.ref(f"legal_department_management.{type_xmlid}", raise_if_not_found=False)
    if not activity_type:
        return
    for record in records:
        activities = record.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)
        if activities:
            activities.sudo().action_feedback(feedback=feedback or records.env._("Closed"))


def render_report(env, report_xmlid, record_ids, data=None):
    """Render a report to PDF, or to HTML when this server has no PDF engine
    (wkhtmltopdf). Returns ``(content, extension, mimetype)``."""
    report = env.ref(report_xmlid)
    try:
        content, kind = env["ir.actions.report"]._render_qweb_pdf(report.report_name, record_ids, data=data)
    except UserError as error:
        _logger.info("PDF engine unavailable, attaching HTML instead: %s", error)
        content, kind = env["ir.actions.report"]._render_qweb_html(report.report_name, record_ids, data=data)
    if kind == "pdf":
        return content, "pdf", "application/pdf"
    return content, "html", "text/html"


def attach_report(env, report_xmlid, record, name, owner=None):
    """Render ``record`` with the report and attach the file to ``owner``
    (default ``record``). Returns the attachment."""
    owner = owner or record
    content, extension, mimetype = render_report(env, report_xmlid, record.ids)
    if isinstance(content, str):
        content = content.encode()
    safe_name = name.replace("/", "-")
    return env["ir.attachment"].create({
        "name": f"{safe_name}.{extension}",
        "raw": content,
        "mimetype": mimetype,
        "res_model": owner._name,
        "res_id": owner.id,
    })


def adopt_attachments(records, field_name="attachment_ids"):
    """Files uploaded on a record before it was first saved are stored with no
    record id, and Odoo lets only their uploader open such files. Attach them
    to the record they were uploaded for, so the people who can read the record
    can read its files. Only the current user's own uploads are moved."""
    uid = records.env.uid
    for record in records:
        orphans = record.sudo()[field_name].filtered(
            lambda a: not a.res_id and a.res_model in (False, record._name) and a.create_uid.id == uid)
        if orphans:
            orphans.write({"res_model": record._name, "res_id": record.id})


def today(record):
    return fields.Date.context_today(record)

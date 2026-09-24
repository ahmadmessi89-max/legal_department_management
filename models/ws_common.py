# -*- coding: utf-8 -*-
"""Helpers shared by the workspace payloads (My Day, agenda, cockpit, palette).

Nothing here searches on its own: the callers search as the reading user, and
these functions only shape what they found. The helpers that translate take the
calling recordset as ``self`` so ``_()`` finds the reader's language.
"""
from odoo import _, fields

M = "legal_department_management"
G_CLERK = f"{M}.group_ldm_clerk"
G_LAWYER = f"{M}.group_legal_user"
G_APPROVER = f"{M}.group_ldm_approver"
G_MANAGER = f"{M}.group_legal_manager"
G_AUDITOR = f"{M}.group_ldm_auditor"
G_BILLING = f"{M}.group_ldm_billing_user"
G_TERMS_DEPARTMENT = f"{M}.group_ldm_terms_department"
G_TERMS_OFFICE = f"{M}.group_ldm_terms_office"

OPEN_STATES = ("draft", "in_progress", "pending_docs")
CLOSED_STATES = ("done", "cancelled")

# Activity types the reminder cron writes for records My Day already shows as
# rows of their own. Showing the reminder too would put every step twice.
REMINDER_TYPES = ("ldm_activity_session", "ldm_activity_deadline", "ldm_activity_step",
                  "ldm_activity_target", "ldm_activity_approval")

# Legal records an activity can hang on and still belong on My Day.
LEGAL_ACTIVITY_MODELS = ("legal.task", "legal.company", "legal.poa", "legal.correspondence", "legal.request",
                         "legal.engagement", "legal.guarantee")

BANDS = ("overdue", "today", "week", "later", "nodate")
BAND_LIMIT = 50


def role_of(self, user):
    """The role key and the one role word the header shows, highest role first."""
    if user.has_group(G_MANAGER):
        return "manager", _("Legal manager")
    if user.has_group(G_APPROVER):
        return "approver", _("Approver")
    if user.has_group(G_LAWYER):
        return "lawyer", _("Lawyer")
    if user.has_group(G_CLERK):
        return "clerk", _("Clerk")
    if user.has_group(G_AUDITOR):
        return "auditor", _("Auditor (read only)")
    if user.has_group(G_BILLING):
        return "billing", _("Billing")
    return "none", ""


def client_word(self, user):
    """How this database calls the party the work is done for (SPEC 14.3)."""
    if user.has_group(G_TERMS_OFFICE):
        return _("Client")
    if user.has_group(G_TERMS_DEPARTMENT):
        return _("Company")
    return _("Client or company")


def band_of(day, today):
    """Which focus band a date falls in. "This week" means the next six days."""
    if not day:
        return "nodate"
    delta = (day - today).days
    if delta < 0:
        return "overdue"
    if delta == 0:
        return "today"
    if delta <= 6:
        return "week"
    return "later"


def iso(day):
    return fields.Date.to_string(day) if day else False


def matter_line(task):
    """Client · body, the second line of every matter row."""
    parts = [task.legal_company_id.name or "", task.department_id.name or ""]
    return " · ".join(p for p in parts if p)


def open_matter(task):
    return {"res_model": "legal.task", "res_id": task.id}

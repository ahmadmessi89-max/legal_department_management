# -*- coding: utf-8 -*-
"""Letter rendering and money formatting shared by the registers and reports.

Letter templates are written by the legal manager, not by a developer, so they
get a fixed vocabulary of placeholders and nothing else. The values are a flat
dict of strings computed here and HTML-escaped before they are substituted; the
template text is escaped too, because it is plain text. There is no QWeb, no
``safe_eval`` and no attribute or index access: ``{client.partner_id.email}``
or ``{client[0]}`` is refused outright, and an unknown ``{placeholder}`` is
printed exactly as written so that a typo shows on the draft instead of
silently disappearing.
"""
import base64
import re
import string

from markupsafe import Markup, escape

from odoo import fields
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, formatLang

# The whole vocabulary. The template form lists the same names with a line of
# explanation each (views/reg_views.xml); keep both in step.
PLACEHOLDERS = (
    "today", "company",
    "matter_number", "matter", "client", "client_address", "client_registration",
    "body", "body_addressee", "court_case_number", "opponent", "our_role", "responsible",
    "letter_number", "letter_date", "their_number", "their_date", "subject",
    "signatory", "signatory_title",
    "poa_number", "poa_date", "poa_notary",
    "guarantee_number", "guarantee_amount", "guarantee_expiry", "bank", "beneficiary",
    "opinion_number",
)

_SIMPLE = re.compile(r"\{([^{}]*)\}")


def _refuse(env, field_name):
    raise UserError(env._(
        "“{%s}” is not a placeholder a letter template may use. Placeholders are plain names "
        "such as {client} or {matter_number}; the list is on the template's Placeholders tab.",
        field_name))


class _Literal:
    """An unknown placeholder, carried through the formatter unchanged."""

    __slots__ = ("text",)

    def __init__(self, text):
        self.text = text


class LdmSafeFormatter(string.Formatter):
    """``str.format`` without its reach: names only, looked up in a flat dict."""

    def __init__(self, env):
        super().__init__()
        self.env = env

    def get_field(self, field_name, args, kwargs):
        if "." in field_name or "[" in field_name:
            _refuse(self.env, field_name)
        if field_name in kwargs:
            return kwargs[field_name], field_name
        return _Literal(field_name), field_name

    def convert_field(self, value, conversion):
        # !r, !s and !a would print Python representations: never wanted.
        if isinstance(value, _Literal) and conversion:
            value.text = f"{value.text}!{conversion}"
        return value

    def format_field(self, value, format_spec):
        if isinstance(value, _Literal):
            return "{%s%s}" % (value.text, f":{format_spec}" if format_spec else "")
        return str(value)


def _fallback(env, source, values):
    """Fill only the well-formed ``{name}`` tokens: used when the text has a
    stray brace that ``str.format`` cannot parse."""
    def one(match):
        name = match.group(1)
        if "." in name or "[" in name:
            _refuse(env, name)
        return str(values[name]) if name in values else match.group(0)
    return _SIMPLE.sub(one, source)


def render_text(env, text, values):
    """Fill ``text`` (plain text with placeholders) from ``values`` and return
    it as safe HTML markup, one paragraph per block of lines."""
    if not text:
        return Markup("")
    safe_values = {key: escape(value if value not in (None, False) else "") for key, value in values.items()}
    source = str(escape(text))
    try:
        rendered = LdmSafeFormatter(env).vformat(source, (), safe_values)
    except ValueError:
        rendered = _fallback(env, source, safe_values)
    blocks = [block.strip("\n") for block in re.split(r"\n\s*\n", rendered.replace("\r\n", "\n"))]
    paragraphs = [Markup("<p>%s</p>") % Markup(block.replace("\n", "<br/>")) for block in blocks if block.strip()]
    return Markup("").join(paragraphs)


def render_line(env, text, values):
    """Fill a one-line text (a subject) and return plain text."""
    if not text:
        return ""
    safe_values = {key: value if value not in (None, False) else "" for key, value in values.items()}
    try:
        return LdmSafeFormatter(env).vformat(text, (), safe_values)
    except ValueError:
        return _fallback(env, text, safe_values)


def money(env, amount, currency=None):
    """An amount with its currency; Iraqi dinars in whole dinars."""
    currency = currency or env.company.currency_id
    unit = "units" if currency.name == "IQD" else "decimals"
    return formatLang(env, amount or 0.0, currency_obj=currency, rounding_unit=unit)


def fdate(env, value, lang=None):
    return format_date(env, value, lang_code=lang) if value else ""


def qr_data_uri(env, value, size=150):
    """A QR code as an inline image, so a PDF needs no request back to the server."""
    png = env["ir.actions.report"].barcode("QR", value, width=size, height=size, quiet=0)
    return "data:image/png;base64,%s" % base64.b64encode(png).decode()


def placeholder_values(env, task=None, letter=None, guarantee=None, poa=None, client=None, body=None,
                       partner=None, lang=None):
    """The flat dict every template is filled from. Every placeholder has a
    value (an empty string when the source does not have it)."""
    env = env(context=dict(env.context, lang=lang)) if lang else env
    task = task or (letter and letter.task_id) or (guarantee and guarantee.task_id) or env["legal.task"]
    client = client or (letter and letter.legal_company_id) or (guarantee and guarantee.legal_company_id) \
        or (poa and poa.principal_company_id) or task.legal_company_id
    body = body or (letter and letter.department_id) or task.department_id
    role_labels = dict(task._fields["our_role"]._description_selection(env)) if task else {}
    values = dict.fromkeys(PLACEHOLDERS, "")
    values.update({
        "today": fdate(env, fields.Date.context_today(task or env["legal.task"]), lang),
        "company": env.company.name or "",
        "matter_number": task.task_number or "",
        "matter": task.name or "",
        "client": client.name if client else "",
        "client_address": (client.address or "") if client else "",
        "client_registration": (client.registration_number or "") if client else "",
        "body": body.name if body else (partner.name if partner else ""),
        "body_addressee": (body.addressee_title or "") if body else "",
        "court_case_number": task.court_case_number or "",
        "opponent": task.opponent_name or "",
        "our_role": role_labels.get(task.our_role, "") if task else "",
        "responsible": task.lawyer_id.name or "",
        "opinion_number": task.opinion_number or "",
    })
    if letter:
        values.update({
            "letter_number": letter.number or "",
            "letter_date": fdate(env, letter.date, lang),
            "their_number": letter.sender_ref or (letter.reply_to_id.sender_ref or letter.reply_to_id.number or ""),
            "their_date": fdate(env, letter.sender_date or letter.reply_to_id.sender_date or letter.reply_to_id.date, lang),
            "subject": letter.name or "",
            "signatory": letter.signatory_id.name or "",
            "signatory_title": letter.signatory_title or "",
        })
    if poa:
        values.update({
            "poa_number": poa.number or "",
            "poa_date": fdate(env, poa.date_issued, lang),
            "poa_notary": poa.notary_office or "",
        })
    if guarantee:
        values.update({
            "guarantee_number": guarantee.number or guarantee.name or "",
            "guarantee_amount": money(env, guarantee.amount, guarantee.currency_id),
            "guarantee_expiry": fdate(env, guarantee.date_expiry, lang),
            "bank": guarantee.bank_id.name or "",
            "beneficiary": guarantee.beneficiary_id.name or "",
        })
    return values

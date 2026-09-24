# -*- coding: utf-8 -*-
"""Helpers for messages to clients and for showing money.

``normalize_iraqi_phone`` turns the ways an Iraqi number is written (0770…,
+964 770…, 00964 770…, Arabic-Indic digits, spaces and dashes) into the digits
WhatsApp's click-to-chat links expect (9647701234567). ``wa_link`` builds the
``wa.me`` link. No WhatsApp API and no paid service is involved: the link opens
WhatsApp on the user's own phone or computer with the text filled in.

``render_placeholders`` fills a template's ``{name}`` placeholders from a flat
dict of plain strings. Only bare lower-case names are replaced; anything else
(``{a.b}``, ``{a[0]}``, format specs) stays as typed, so a template can never
reach an attribute or run code.
"""
import re
from urllib.parse import quote

from odoo.tools.misc import formatLang

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
IRAQ = "964"


def normalize_iraqi_phone(phone):
    """Return the international digits of ``phone`` (e.g. ``9647701234567``),
    or False when it cannot be a reachable number."""
    if not phone:
        return False
    value = str(phone).translate(_DIGITS).strip()
    international = value.startswith("+") or value.startswith("00")
    digits = re.sub(r"\D", "", value)
    if value.startswith("00"):
        digits = digits[2:]
    if not digits:
        return False
    if digits.startswith(IRAQ) and (international or len(digits) >= 12):
        rest = digits[len(IRAQ):]
        # "+964 0770…": the trunk zero typed after the country code.
        digits = IRAQ + (rest[1:] if rest.startswith("0") else rest)
    elif international:
        pass
    elif digits.startswith("0"):
        digits = IRAQ + digits[1:]
    elif digits.startswith("7") and len(digits) == 10:
        digits = IRAQ + digits
    else:
        return False
    return digits if 10 <= len(digits) <= 15 else False


def wa_link(phone, text=""):
    """``https://wa.me/<digits>?text=…`` for ``phone``, or False."""
    digits = normalize_iraqi_phone(phone)
    if not digits:
        return False
    return f"https://wa.me/{digits}" + (f"?text={quote(text)}" if text else "")


def render_placeholders(text, values):
    """Replace ``{name}`` with ``values[name]``; unknown names stay literal."""
    if not text:
        return ""
    return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)


def money_text(env, amounts):
    """``amounts`` is an iterable of (currency, amount). Returns the non-zero
    ones formatted in the user's language, joined with a middle dot, largest
    first; "" when everything is zero."""
    parts = []
    for currency, amount in sorted(amounts, key=lambda pair: -abs(pair[1])):
        if currency and not currency.is_zero(amount):
            parts.append(formatLang(env, amount, currency_obj=currency))
    return " · ".join(parts)

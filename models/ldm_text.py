# -*- coding: utf-8 -*-
"""Arabic-aware text normalisation shared by search, duplicate checks, the
reference-data merge and the conflict-of-interest check.

Iraqi names are typed many ways: أ/إ/آ/ا, ة/ه, ى/ي, with or without
diacritics and tatweel, with Arabic-Indic or Latin digits, with or without the
definite article. Two spellings of one body or one person must compare equal.
"""
import re

_TASHKEEL = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
_SPACES = re.compile(r"\s+")
_PUNCT = re.compile(r"[\.,;:!\?\-_/\\\(\)\[\]\"'«»،؛؟]+")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و", "ئ": "ي"})


def normalize(text, drop_article=False):
    """Return a comparison key for ``text``: lower case, one space between words,
    no diacritics, no tatweel, unified letters and digits, no punctuation.
    With ``drop_article`` the Arabic definite article is removed from each word."""
    if not text:
        return ""
    value = str(text).strip().lower()
    value = _TASHKEEL.sub("", value).replace(_TATWEEL, "")
    value = value.translate(_DIGITS).translate(_LETTERS)
    value = _PUNCT.sub(" ", value)
    words = [w for w in _SPACES.split(value) if w]
    if drop_article:
        words = [w[2:] if w.startswith("ال") and len(w) > 3 else w for w in words]
    return " ".join(words)


def tokens(text):
    """Words of ``text`` after normalisation, without the article, for fuzzy matching."""
    return [w for w in normalize(text, drop_article=True).split(" ") if len(w) > 1]


# Words written before a name that do not name anyone: titles of people and the
# generic words of a company's name.
_NAME_PREFIXES = {normalize(w) for w in (
    "شركة", "مجموعة", "فرع", "مكتب", "السيد", "السيدة", "الأستاذ", "الأستاذة", "المحامي", "المحامية",
    "المتمرن", "المتمرنة", "المستشار", "المستشارة", "القاضي", "الدكتور", "الدكتورة", "د", "م",
    "company", "the", "mr", "mrs", "ms", "dr")}


def initial(name):
    """The letter that stands for a person or a client on a card or an avatar:
    the first letter of the first word that names them, after any title and
    after the Arabic article ("المحامية زينب الجبوري" gives "ز", "شركة الرافدين"
    gives "ر"), where taking the first letter would give most Iraqi names the
    same "ا"."""
    words = [w for w in (name or "").split() if w]
    while len(words) > 1 and normalize(words[0]) in _NAME_PREFIXES:
        words = words[1:]
    word = words[0].strip(".") if words else ""
    if word.startswith("ال") and len(word) > 3:
        word = word[2:]
    return word[:1].upper() or "?"

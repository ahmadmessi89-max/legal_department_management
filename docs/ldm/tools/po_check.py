"""Check an Arabic .po catalogue: empty entries, English left in Arabic entries,
emoji, placeholders that differ between msgid and msgstr (a broken %s or
{name} crashes the screen that uses it), and code strings Odoo would not read.

Usage: python docs/ldm/tools/po_check.py [custom_addons/legal_department_management/i18n/ar.po] [--fix]
Exit code 1 when anything needs fixing.

Odoo 19 uses a code string's translation (``_()`` in Python, ``_t`` in
JavaScript) only when its entry carries the ``#. odoo-python`` or
``#. odoo-javascript`` comment; without it the English shows, with no warning.
An entry added by hand is easy to leave without it. ``--fix`` adds the comment
from the entry's ``#: code:`` reference.
"""
import re
import sys

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⏳⌛]")
ARABIC = re.compile("[؀-ۿ]")
PLACEHOLDER = re.compile(r"%\([a-z_]+\)[sd]|%[sd]|\{[a-z_0-9]*\}")
DEFAULT = "custom_addons/legal_department_management/i18n/ar.po"
MARKS = ("#. odoo-python", "#. odoo-javascript")


def entries(path):
    msgid, msgstr, target, comments = [], [], None, []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#"):
            if target == "msgstr":
                yield "".join(msgid), "".join(msgstr), comments
                msgid, msgstr, target, comments = [], [], None, []
            comments.append(line)
        elif line.startswith("msgid "):
            if target == "msgstr":
                yield "".join(msgid), "".join(msgstr), comments
                comments = []
            msgid, msgstr, target = [line[7:-1]], [], "msgid"
        elif line.startswith("msgstr "):
            msgstr, target = [line[8:-1]], "msgstr"
        elif line.startswith('"') and target:
            (msgid if target == "msgid" else msgstr).append(line[1:-1])
    if target == "msgstr":
        yield "".join(msgid), "".join(msgstr), comments


def unmarked(comments):
    return any(c.startswith("#: code:") for c in comments) and not any(c in MARKS for c in comments)


def add_marks(path):
    """Insert the missing odoo-python / odoo-javascript comment before the
    first code reference of every entry that lacks one."""
    blocks = open(path, encoding="utf-8").read().split("\n\n")
    fixed = 0
    for i, block in enumerate(blocks):
        lines = block.split("\n")
        if not unmarked([l for l in lines if l.startswith("#")]):
            continue
        refs = [l for l in lines if l.startswith("#: code:")]
        web = any(r.split(":")[2].endswith((".js", ".xml")) for r in refs)
        lines.insert(lines.index(refs[0]), MARKS[1] if web else MARKS[0])
        blocks[i] = "\n".join(lines)
        fixed += 1
    if fixed:
        open(path, "w", encoding="utf-8", newline="\n").write("\n\n".join(blocks))
    return fixed


def main(path, fix=False):
    if fix:
        print(f"code marks added: {add_marks(path)}")
    empty, english, emoji, placeholders, marks, total = [], [], [], [], [], 0
    for msgid, msgstr, comments in entries(path):
        if not msgid:
            continue
        total += 1
        if unmarked(comments):
            marks.append(msgid)
        if not msgstr:
            empty.append(msgid)
            continue
        if EMOJI.search(msgstr):
            emoji.append(msgid)
        # identity translations of technical tokens are allowed (placeholders,
        # markup, a number pattern such as 07XX XXX XXXX); English sentences are not
        words = re.sub(r"<[^>]*>|\bX+\b", " ", PLACEHOLDER.sub(" ", msgstr))
        if not ARABIC.search(msgstr) and re.search(r"[A-Za-z]{3,}.*\s.*[A-Za-z]{3,}", words):
            english.append(msgid)
        if sorted(PLACEHOLDER.findall(msgid)) != sorted(PLACEHOLDER.findall(msgstr)):
            placeholders.append(msgid)
    print(f"{total} entries · {len(empty)} empty · {len(english)} English · {len(emoji)} emoji · "
          f"{len(placeholders)} placeholder mismatches · {len(marks)} code strings Odoo would not read")
    for label, items in (("EMPTY", empty), ("ENGLISH", english), ("EMOJI", emoji),
                         ("PLACEHOLDER", placeholders), ("UNMARKED", marks)):
        for item in items[:30]:
            print(f"{label}: {item[:120]}")
    return 1 if (empty or english or emoji or placeholders or marks) else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(args[0] if args else DEFAULT, fix="--fix" in sys.argv))

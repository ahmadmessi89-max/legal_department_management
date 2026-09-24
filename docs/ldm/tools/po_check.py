"""Check an Arabic .po catalogue: empty entries, English left in Arabic entries,
emoji, and placeholders that differ between msgid and msgstr (a broken %s or
{name} crashes the screen that uses it).

Usage: python docs/ldm/tools/po_check.py custom_addons/legal_department_management/i18n/ar.po
Exit code 1 when anything needs fixing.
"""
import re
import sys

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⏳⌛]")
ARABIC = re.compile("[؀-ۿ]")
PLACEHOLDER = re.compile(r"%\([a-z_]+\)[sd]|%[sd]|\{[a-z_0-9]*\}")


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


def main(path):
    empty, english, emoji, placeholders, total = [], [], [], [], 0
    for msgid, msgstr, _comments in entries(path):
        if not msgid:
            continue
        total += 1
        if not msgstr:
            empty.append(msgid)
            continue
        if EMOJI.search(msgstr):
            emoji.append(msgid)
        # identity translations of technical tokens are allowed; English sentences are not
        if not ARABIC.search(msgstr) and re.search(r"[A-Za-z]{3,}.*\s.*[A-Za-z]{3,}", msgstr):
            english.append(msgid)
        if sorted(PLACEHOLDER.findall(msgid)) != sorted(PLACEHOLDER.findall(msgstr)):
            placeholders.append(msgid)
    print(f"{total} entries · {len(empty)} empty · {len(english)} English · {len(emoji)} emoji · "
          f"{len(placeholders)} placeholder mismatches")
    for label, items in (("EMPTY", empty), ("ENGLISH", english), ("EMOJI", emoji), ("PLACEHOLDER", placeholders)):
        for item in items[:30]:
            print(f"{label}: {item[:120]}")
    return 1 if (empty or english or emoji or placeholders) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

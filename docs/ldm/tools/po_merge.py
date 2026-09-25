"""Add translated entries to the Arabic catalogue from a fresh export.

  py -3.11 docs/ldm/tools/po_merge.py <export.po> <translations.json> [--drop-unused]

The export (odoo-bin i18n export) gives each string with its references and
its odoo-python / odoo-javascript mark, which Odoo needs to use a code
string's translation; the JSON gives {English: Arabic} for the new ones.
Every entry takes its references and marks from the export and keeps its
translation: a word first used in a menu and later in Python code (Agenda)
needs the odoo-python mark it did not have. With --drop-unused, entries the
export no longer has are removed. Run po_check.py afterwards.
"""
import json
import re
import sys

PO = "custom_addons/legal_department_management/i18n/ar.po"
ENTRY = re.compile(r'^msgid "(.*?)"\n((?:".*"\n)*)msgstr "(.*?)"((?:\n".*")*)', re.M)


def parse(text):
    """{msgid: block} for every entry after the header."""
    blocks = text.split("\n\n")
    out = {}
    for block in blocks[1:]:
        m = ENTRY.search(block)
        if m:
            msgid = m.group(1) + "".join(re.findall(r'"(.*)"', m.group(2)))
            if msgid:
                out[msgid] = block
    return blocks[0], out


def quote(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def main():
    export_path, json_path = sys.argv[1], sys.argv[2]
    drop = "--drop-unused" in sys.argv
    header, catalogue = parse(open(PO, encoding="utf-8").read())
    _header, export = parse(open(export_path, encoding="utf-8").read())
    arabic = json.load(open(json_path, encoding="utf-8"))
    added = []
    for msgid, arabic_text in arabic.items():
        if msgid not in export:
            sys.exit(f"not in the export: {msgid!r}")
        block = export[msgid]
        head = block[:ENTRY.search(block).start()]
        catalogue[msgid] = f'{head}msgid "{quote(msgid)}"\nmsgstr "{quote(arabic_text)}"'
        added.append(msgid)
    refreshed = 0
    for msgid, block in list(catalogue.items()):
        if msgid in added or msgid not in export:
            continue
        head = export[msgid][:ENTRY.search(export[msgid]).start()]
        body = block[ENTRY.search(block).start():]
        if block[:ENTRY.search(block).start()] != head:
            catalogue[msgid] = head + body
            refreshed += 1
    removed = []
    if drop:
        for msgid in list(catalogue):
            if msgid not in export:
                removed.append(msgid)
                del catalogue[msgid]
    text = header + "\n\n" + "\n\n".join(catalogue.values()).rstrip("\n") + "\n"
    open(PO, "w", encoding="utf-8", newline="\n").write(text)
    print(f"added or updated {len(added)}, references refreshed {refreshed}, removed {len(removed)}: {removed}")


if __name__ == "__main__":
    main()

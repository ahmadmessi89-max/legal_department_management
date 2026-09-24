"""Split an exported .po into translation chunks and merge the translations back.

  python docs/ldm/tools/po_split.py split <export.po> <outdir> <chunks>
      writes <outdir>/chunk_<n>.json: [{"id", "msgid", "where"}] for every
      entry still empty, grouped by source file so a translator sees related
      strings together.
  python docs/ldm/tools/po_split.py merge <export.po> <outdir> <result.po>
      reads <outdir>/chunk_<n>.ar.json ({"<id>": "<arabic>"}) and fills the
      msgstr of the matching entries. Entries whose msgid is already Arabic, or
      is only a technical token, are filled with the msgid itself (the
      catalogue's convention for identity translations).
"""
import glob
import json
import os
import re
import sys

import polib

ARABIC = re.compile("[؀-ۿ]")


def identity(msgid):
    if ARABIC.search(msgid):
        return True
    stripped = re.sub(r"%\([a-z_]+\)[sd]|%[sd]|\{[a-z_0-9]*\}", "", msgid).strip()
    return not re.search(r"[A-Za-z]{2,}", stripped)


def split(path, outdir, chunks):
    po = polib.pofile(path, wrapwidth=0)
    os.makedirs(outdir, exist_ok=True)
    todo = []
    for index, entry in enumerate(po):
        if entry.msgstr or not entry.msgid or identity(entry.msgid):
            continue
        where = sorted({occ[0].replace("addons/legal_department_management/", "") for occ in entry.occurrences})
        todo.append({"id": index, "msgid": entry.msgid, "where": where[:3]})
    todo.sort(key=lambda item: (item["where"][0] if item["where"] else "", item["id"]))
    size = -(-len(todo) // chunks)
    for n in range(chunks):
        part = todo[n * size:(n + 1) * size]
        with open(os.path.join(outdir, f"chunk_{n + 1}.json"), "w", encoding="utf-8") as fh:
            json.dump(part, fh, ensure_ascii=False, indent=1)
        print(f"chunk_{n + 1}.json: {len(part)} strings")


def merge(path, outdir, result):
    po = polib.pofile(path, wrapwidth=0)
    translations = {}
    for file in sorted(glob.glob(os.path.join(outdir, "chunk_*.ar.json"))):
        translations.update({int(k): v for k, v in json.load(open(file, encoding="utf-8")).items()})
    filled = identities = 0
    for index, entry in enumerate(po):
        if not entry.msgid:
            continue
        if index in translations and translations[index].strip():
            entry.msgstr = translations[index]
            filled += 1
        elif not entry.msgstr and identity(entry.msgid):
            entry.msgstr = entry.msgid
            identities += 1
        if "fuzzy" in entry.flags:
            entry.flags.remove("fuzzy")
    po.save(result)
    print(f"{filled} translated, {identities} identity entries, written to {result}")


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "split":
        split(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        merge(sys.argv[2], sys.argv[3], sys.argv[4])

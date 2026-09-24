"""Compact translation sheets for the Arabic catalogue.

po_split.py cuts the exported catalogue into chunk_<n>.json slices; this tool
turns a slice into a one-line-per-string sheet that is quick to translate, and
turns the translated sheet back into the chunk_<n>.ar.json that po_split.py
merges. Line breaks and tabs inside a string are written as \\n and \\t.

  python docs/ldm/tools/i18n_tsv.py sheet <workdir> <n>
      writes <workdir>/c<n>.tsv:  id <TAB> where <TAB> English
  python docs/ldm/tools/i18n_tsv.py check <workdir> <n>
      reads <workdir>/c<n>.ar.tsv:  id <TAB> Arabic
      and writes <workdir>/chunk_<n>.ar.json when every id is present and
      every placeholder (%s, %(x)s, {x}, %%) and HTML tag matches the English.
      A tag may change only its title="..." text.
"""
import json
import os
import re
import sys

BS = chr(92)
TOKEN = re.compile(r"%\([a-z_0-9]+\)[sd]|%%|%[sd]|\{[a-z_0-9]*\}|<[^>]+>")


def esc(text):
    return text.replace(BS, BS + BS).replace("\r", BS + "r").replace("\n", BS + "n").replace("\t", BS + "t")


def unesc(text):
    out, i = [], 0
    while i < len(text):
        if text[i] == BS and i + 1 < len(text) and text[i + 1] in "nrt" + BS:
            out.append({"n": "\n", "r": "\r", "t": "\t", BS: BS}[text[i + 1]])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def tokens(text):
    return sorted(re.sub(r'title="[^"]*"', 'title=""', t) for t in TOKEN.findall(text))


def sheet(workdir, n):
    rows = json.load(open(os.path.join(workdir, f"chunk_{n}.json"), encoding="utf-8"))
    lines = []
    for row in rows:
        where = row["where"][0].split(":")[-1] if row["where"] else ""
        lines.append(f'{row["id"]}\t{where}\t{esc(row["msgid"])}')
    with open(os.path.join(workdir, f"c{n}.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"c{n}.tsv: {len(lines)} strings")


def check(workdir, n):
    source = {row["id"]: row["msgid"] for row in json.load(open(os.path.join(workdir, f"chunk_{n}.json"), encoding="utf-8"))}
    done = {}
    for line in open(os.path.join(workdir, f"c{n}.ar.tsv"), encoding="utf-8").read().splitlines():
        if line.strip():
            key, text = line.split("\t", 1)
            done[int(key)] = unesc(text)
    problems = [f"missing {k}: {v[:60]}" for k, v in source.items() if k not in done]
    problems += [f"placeholders {k}" for k, v in source.items() if k in done and tokens(v) != tokens(done[k])]
    problems += [f"unknown id {k}" for k in done if k not in source]
    for problem in problems:
        print(problem)
    print(f"slice {n}: {len(done)}/{len(source)} translated, {len(problems)} problems")
    if problems:
        sys.exit(1)
    with open(os.path.join(workdir, f"chunk_{n}.ar.json"), "w", encoding="utf-8") as fh:
        json.dump({str(k): done[k] for k in source}, fh, ensure_ascii=False, indent=0)
    print(f"written chunk_{n}.ar.json")


if __name__ == "__main__":
    {"sheet": sheet, "check": check}[sys.argv[1]](sys.argv[2], int(sys.argv[3]))

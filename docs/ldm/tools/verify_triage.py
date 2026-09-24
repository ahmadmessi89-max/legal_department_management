"""Summarise a verification round's results.json by kind of problem.

  python docs/ldm/tools/verify_triage.py docs/ldm/evidence/<round>/results.json

Prints the counts per kind, then every distinct leaked text (Latin on Arabic
screens, Arabic on English screens) with how often and where it appears, so a
leak can be sorted into interface text (a defect) or data typed in the other
language (not a defect), and the failed screens with their error.
"""
import json
import sys
from collections import Counter, defaultdict

rows = json.load(open(sys.argv[1], encoding="utf-8"))
bad = [r for r in rows if r["problems"]]
print(f"{len(rows)} captures, {len(bad)} with problems")
kinds = Counter(p.split(" [")[0].split(" ")[0] if not p[0].isdigit() else p.split(" ", 1)[1] for r in bad for p in r["problems"])
for kind, count in kinds.most_common():
    print(f"  {count:4}  {kind}")

latin, arabic = defaultdict(set), defaultdict(set)
for r in rows:
    tag = f"{r['role']}/{r['width']}/{r['screen']}"
    for word in r.get("latin_leak") or []:
        latin[word].add(tag)
    for text in r.get("arabic_leak") or []:
        arabic[text[:80]].add(tag)
if latin:
    print("\nLatin on Arabic screens:")
    for word, where in sorted(latin.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(where):3}  {word:24} {', '.join(sorted(where)[:4])}")
if arabic:
    print("\nArabic on English screens:")
    for text, where in sorted(arabic.items(), key=lambda kv: -len(kv[1]))[:80]:
        print(f"  {len(where):3}  {text:60} {', '.join(sorted(where)[:3])}")
failed = [r for r in rows if r.get("failed") or r.get("error_dialog") or r.get("page_errors")]
if failed:
    print("\nFailed screens:")
    for r in failed:
        print(f"  {r['role']}/{r['lang']}/{r['width']}/{r['screen']}: "
              f"{(r.get('failed') or '').splitlines()[0][:120] if r.get('failed') else ''}"
              f"{' error dialog' if r.get('error_dialog') else ''} {r.get('page_errors') or ''}")
others = [r for r in bad if any(k in p for p in r["problems"] for k in ("columns", "header buttons", "overflow", "top menus", "emoji"))]
if others:
    print("\nLayout budgets:")
    for r in others:
        print(f"  {r['role']}/{r['lang']}/{r['width']}/{r['screen']}: {'; '.join(r['problems'])}")

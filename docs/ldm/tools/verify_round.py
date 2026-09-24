"""Verification round for legal_department_management: every screen as every role,
in Arabic and English, at desktop and phone width, with automatic checks.

Usage:
    py -3.11 docs/ldm/tools/verify_round.py --base http://127.0.0.1:8110 --db ldm_pro \
        --plan docs/ldm/tools/verify_plan.json --out docs/ldm/evidence/<round> [--only lawyer]

The plan lists users (login, password, role) and screens (name, path, wait, clicks, kind).
For each user × language × viewport it saves a screenshot and a row in results.json:
  - error dialogs and page errors (a failed navigation is reported, never presented as evidence)
  - latin_leak: Latin words visible on an Arabic screen (identifiers such as CASE/2026/… allowed)
  - arabic_leak: Arabic visible on an English screen outside data cells
  - emoji found in visible text
  - form_buttons: visible primary buttons in a form's status bar area (budget 2)
  - list_columns: visible default columns in a list (budget 6)
  - overflow_x: horizontal overflow at phone width
  - menu_top: top-level menu entries of the Legal app (budget 7, managers exempt)
Waits on selectors, never on networkidle: the bus keeps a long-poll open forever.
"""
import argparse
import json
import os
import re
import sys
import time
import xmlrpc.client

from playwright.sync_api import sync_playwright

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⏳⌛]")
LATIN_WORD = re.compile(r"\b[A-Za-z]{3,}\b")
ARABIC = re.compile("[؀-ۿ]")
ALLOWED_LATIN = {"CASE", "IQD", "USD", "PDF", "QR", "Odoo", "OdooBot", "WhatsApp", "Ctrl", "Alt", "Shift", "Enter"}

CHECK_JS = r"""
() => {
  const visible = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const root = document.querySelector('.o_action_manager') || document.body;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const texts = [];
  while (walker.nextNode()) {
    const n = walker.currentNode; const t = n.textContent.trim();
    if (!t || !n.parentElement || !visible(n.parentElement)) continue;
    if (n.parentElement.closest('.o_field_widget input, textarea, .o_data_cell, .o_kanban_record .o_field_char, .o_field_many2one, .o_mail_body, .o-mail-Message-body, .o_field_html, code, pre')) continue;
    texts.push(t);
  }
  const form = document.querySelector('.o_form_view');
  let formButtons = null;
  if (form) {
    const bar = form.querySelector('.o_form_statusbar .o_statusbar_buttons');
    // an overflow menu ("More actions") is how the budget is kept, not a third button
    formButtons = bar ? [...bar.querySelectorAll('button')].filter(b => visible(b) && !b.matches('.dropdown-toggle, [aria-haspopup], .o-dropdown')).length : 0;
  }
  const list = document.querySelector('.o_list_view table');
  const listColumns = list ? [...list.querySelectorAll('thead th')].filter(th => visible(th) && !th.classList.contains('o_list_record_selector') && !th.classList.contains('o_list_actions_header') && th.textContent.trim()).length : null;
  const overflowX = document.scrollingElement.scrollWidth > window.innerWidth + 2;
  const menuTop = [...document.querySelectorAll('.o_menu_sections > .dropdown-toggle, .o_menu_sections > a, .o_menu_sections > button')].filter(visible).length;
  return { texts, formButtons, listColumns, overflowX, menuTop };
}
"""


def analyse(raw, lang):
    joined = " ".join(raw["texts"])
    row = {"form_buttons": raw["formButtons"], "list_columns": raw["listColumns"],
           "overflow_x": raw["overflowX"], "menu_top": raw["menuTop"]}
    row["emoji"] = sorted(set(EMOJI.findall(joined)))
    if lang.startswith("ar"):
        words = [w for w in LATIN_WORD.findall(joined) if w not in ALLOWED_LATIN]
        row["latin_leak"] = sorted(set(words))[:40]
    else:
        row["arabic_leak"] = [t for t in raw["texts"] if ARABIC.search(t)][:20]
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8110")
    ap.add_argument("--db", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--langs", default="ar_001,en_US")
    ap.add_argument("--viewports", default="1440x900,390x844")
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for user in plan["users"]:
            if a.only and user["role"] not in a.only.split(","):
                continue
            common = xmlrpc.client.ServerProxy(f"{a.base}/xmlrpc/2/common")
            models = xmlrpc.client.ServerProxy(f"{a.base}/xmlrpc/2/object")
            uid = common.authenticate(a.db, user["login"], user["password"], {})
            # the round switches the user's language; it is put back afterwards
            own_lang = models.execute_kw(a.db, uid, user["password"], "res.users", "read",
                                         [[uid], ["lang"]])[0]["lang"]
            for lang in a.langs.split(","):
                for vp in a.viewports.split(","):
                    width, height = (int(x) for x in vp.split("x"))
                    ctx = browser.new_context(viewport={"width": width, "height": height},
                                              locale="ar-IQ" if lang.startswith("ar") else "en-US")
                    page = ctx.new_page()
                    console, perr = [], []
                    page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
                    page.on("pageerror", lambda e: perr.append(str(e)))
                    # the user's language is part of the plan: the user sets it on
                    # their own record before logging in (lang is self-writeable)
                    models.execute_kw(a.db, uid, user["password"], "res.users", "write", [[uid], {"lang": lang}])
                    page.goto(f"{a.base}/web/login?db={a.db}")
                    page.fill("input[name=login]", user["login"])
                    page.fill("input[name=password]", user["password"])
                    page.click("button[type=submit]")
                    # any loaded web client counts (an administrator lands in
                    # Discuss, which has no main navbar); a login that never
                    # loads is recorded and the round goes on
                    try:
                        page.wait_for_selector(".o_main_navbar, .o_action_manager, .o-mail-Discuss", timeout=60000)
                    except Exception as exc:
                        results.append({"user": user["login"], "role": user["role"], "lang": lang, "width": width,
                                        "screen": "login", "failed": str(exc)[:400], "problems": ["FAILED login"]})
                        print(f"FAIL {user['role']}_{lang[:2]}_{width}_login", flush=True)
                        ctx.close()
                        continue
                    for screen in plan["screens"]:
                        if screen.get("roles") and user["role"] not in screen["roles"]:
                            continue
                        console.clear(); perr.clear()
                        tag = f"{user['role']}_{lang[:2]}_{width}_{screen['name']}"
                        row = {"user": user["login"], "role": user["role"], "lang": lang, "width": width,
                               "screen": screen["name"]}
                        try:
                            # one retry after a reload: a slow first load of an action is not a defect,
                            # a screen that fails twice is reported
                            for attempt in (1, 2):
                                try:
                                    page.goto(a.base + screen["path"])
                                    page.wait_for_selector(screen.get("wait", ".o_action_manager > *"), timeout=30000)
                                    for click in screen.get("clicks", []):
                                        page.click(click, timeout=15000)
                                        time.sleep(0.8)
                                    break
                                except Exception:
                                    if attempt == 2:
                                        raise
                                    row["retried"] = True
                            # the mouse leaves the page, so a tooltip from the last click
                            # or a hovered row is not part of the picture
                            page.mouse.move(-5, -5)
                            time.sleep(screen.get("settle", 1.5))
                            row["error_dialog"] = page.locator(".o_error_dialog").count() > 0
                            row.update(analyse(page.evaluate(CHECK_JS), lang))
                            shot = os.path.join(a.out, tag + ".png")
                            page.screenshot(path=shot, full_page=screen.get("full", False))
                            row["shot"] = shot
                        except Exception as exc:
                            row["failed"] = str(exc)[:400]
                        row["console_errors"] = list(console)[:5]
                        row["page_errors"] = list(perr)[:5]
                        problems = []
                        if row.get("failed"): problems.append("FAILED")
                        if row.get("error_dialog"): problems.append("error dialog")
                        if row["page_errors"]: problems.append("page error")
                        if row.get("emoji"): problems.append("emoji")
                        if row.get("latin_leak"): problems.append(f"latin {row['latin_leak'][:6]}")
                        if row.get("arabic_leak"): problems.append("arabic in english")
                        if (row.get("form_buttons") or 0) > 2: problems.append(f"{row['form_buttons']} header buttons")
                        if (row.get("list_columns") or 0) > 6: problems.append(f"{row['list_columns']} columns")
                        if width < 500 and row.get("overflow_x"): problems.append("horizontal overflow")
                        if user["role"] not in ("manager", "admin") and (row.get("menu_top") or 0) > 7:
                            problems.append(f"{row['menu_top']} top menus")
                        row["problems"] = problems
                        results.append(row)
                        print(("ok   " if not problems else "FAIL ") + tag + ("" if not problems else "  " + "; ".join(problems)), flush=True)
                    ctx.close()
                    # saved after every context, so a crash keeps what was seen
                    json.dump(results, open(os.path.join(a.out, "results.json"), "w", encoding="utf-8"),
                              ensure_ascii=False, indent=1)
            models.execute_kw(a.db, uid, user["password"], "res.users", "write", [[uid], {"lang": own_lang}])
        browser.close()
    json.dump(results, open(os.path.join(a.out, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    bad = [r for r in results if r["problems"]]
    print(f"{len(results)} captures, {len(bad)} with problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

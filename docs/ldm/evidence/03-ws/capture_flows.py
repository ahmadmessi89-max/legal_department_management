"""Workspace (W) screens that need interaction: typing in the New matter
dialog, opening the palette, choosing a row in the approvals inbox, filling
the hand-over dialog. Complements docs/ldm/tools/capture.py.

Usage:
    py -3.11 docs/ldm/evidence/03-ws/capture_flows.py --base http://127.0.0.1:8104 --db ldm_w \
        --out docs/ldm/evidence/03-ws/final --ids '{"suit": 216, ...}' [--width 390 --height 844 --prefix m_]
        [--only lawyer,clerk]

Every screen records console errors, page errors, an open Odoo error dialog,
horizontal overflow (scrollWidth > viewport) and, on a matter form, how many
header buttons are visible. Waits on selectors, never on networkidle.
"""
import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:8104")
ap.add_argument("--db", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--ids", required=True)
ap.add_argument("--width", type=int, default=1440)
ap.add_argument("--height", type=int, default=900)
ap.add_argument("--prefix", default="")
ap.add_argument("--only", default="")
a = ap.parse_args()
ids = json.loads(a.ids)
os.makedirs(a.out, exist_ok=True)
mobile = a.width < 600

PROBE = """() => {
    const doc = document.documentElement;
    const header = document.querySelector('.o_form_statusbar .o_statusbar_buttons');
    const visible = header ? [...header.children].filter(el => el.offsetParent !== null) : [];
    const sizes = [...document.querySelectorAll('.o_action_manager *')]
        .filter(el => el.offsetParent !== null && el.childElementCount === 0 && (el.textContent || '').trim())
        .map(el => ({size: parseFloat(getComputedStyle(el).fontSize), text: el.textContent.trim().slice(0, 40)}));
    sizes.sort((x, y) => y.size - x.size);
    return {
        overflow_x: doc.scrollWidth > window.innerWidth + 1,
        header_buttons: visible.length,
        header_labels: visible.map(el => (el.textContent || el.title || '').trim()),
        largest_text: sizes[0] || null,
    };
}"""


def run_user(p, login, steps):
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": a.width, "height": a.height}, locale="ar-IQ",
                              is_mobile=mobile, has_touch=mobile)
    page = ctx.new_page()
    console, perr = [], []
    page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: perr.append(str(e)))
    page.goto(f"{a.base}/web/login?db={a.db}")
    page.fill("input[name=login]", login)
    page.fill("input[name=password]", login)
    page.click("button[type=submit]")
    page.wait_for_selector(".o_main_navbar", timeout=60000)
    rows = []
    for name, fn in steps:
        console.clear()
        perr.clear()
        row = {"name": f"{a.prefix}{name}", "user": login}
        try:
            fn(page)
            time.sleep(1.2)
            row["error_dialog"] = page.locator(".o_error_dialog").count() > 0
            row.update(page.evaluate(PROBE))
            shot = os.path.join(a.out, f"{a.prefix}{name}.png")
            page.screenshot(path=shot, full_page=False)
            row["shot"] = shot
        except Exception as exc:  # noqa: BLE001 - reported, never presented as evidence
            row["failed"] = str(exc)[:400]
        row["console_errors"] = list(console)
        row["page_errors"] = list(perr)
        rows.append(row)
        bad = row.get("failed") or row.get("error_dialog") or perr
        print(("FAIL " if bad else "ok   ") + row["name"], row.get("failed", ""), flush=True)
    browser.close()
    return rows


def goto(path, wait):
    def fn(page):
        page.goto(a.base + path)
        page.wait_for_selector(wait, timeout=30000)
    return fn


def seq(*fns):
    def fn(page):
        for f in fns:
            f(page)
    return fn


def click(selector, wait=None, pause=0.6):
    def fn(page):
        page.click(selector, timeout=15000)
        if wait:
            page.wait_for_selector(wait, timeout=15000)
        time.sleep(pause)
    return fn


def pick_many2one(field_name, text, index=0):
    """Type in a many2one of the open dialog and choose a suggestion."""
    def fn(page):
        sel = f".modal div[name='{field_name}'] input"
        if page.get_attribute(sel, "readonly") is not None:
            # On a phone Odoo opens a search dialog instead of a dropdown.
            page.click(sel)
            rows = page.locator(".modal:last-of-type .o_data_row, "
                                ".modal:last-of-type .o_kanban_record:not(.o_kanban_ghost)")
            rows.first.wait_for(timeout=15000)
            time.sleep(0.6)
            rows.filter(has_text=text).nth(index).click()
            time.sleep(1.0)
            return
        page.click(sel)
        page.fill(sel, text)
        page.wait_for_selector(".o-autocomplete--dropdown-item", timeout=15000)
        time.sleep(0.6)
        page.locator(".o-autocomplete--dropdown-item").nth(index).click()
        time.sleep(0.8)
    return fn


def scroll_to(selector):
    def fn(page):
        page.locator(selector).first.scroll_into_view_if_needed(timeout=10000)
        page.evaluate("(s) => document.querySelector(s).scrollIntoView({block: 'start'})", selector)
        time.sleep(0.5)
    return fn


def fill(selector, text):
    def fn(page):
        page.fill(selector, text)
        time.sleep(0.4)
    return fn


def palette(text):
    def fn(page):
        page.keyboard.press("Control+k")
        page.wait_for_selector(".o_command_palette input", timeout=10000)
        page.fill(".o_command_palette input", text)
        time.sleep(1.8)
    return fn


def matter(key):
    return goto(f"/odoo/matters/{ids[key]}", ".o_ldm_matter_form .o_ldm_next_wrap")


MY_DAY = goto("/odoo/my-day", ".o_ldm_my_day")
NEW = click(".o_ldm_md_new", ".o_ldm_quick_create")
FLOWS = {
    "zainab": [
        ("lawyer_my_day", MY_DAY),
        ("lawyer_cockpit_lawsuit", matter("suit")),
        ("lawyer_cockpit_lawsuit_more_menu", seq(matter("suit"), click(".o_ldm_more_toggle", ".dropdown-menu"))),
        ("lawyer_cockpit_government", matter("tax")),
        ("lawyer_cockpit_documents_tab", seq(matter("tax"), click(".o_notebook .nav-link[name='documents']",
                                                                   ".o_ldm_documents"),
                                                  scroll_to(".o_notebook"))),
        ("lawyer_quick_create_empty", seq(MY_DAY, NEW)),
        ("lawyer_quick_create_government", seq(MY_DAY, NEW, pick_many2one("template_id", "حكومية"),
                                               pick_many2one("legal_company_id", "الرافدين"))),
        ("lawyer_quick_create_lawsuit", seq(MY_DAY, NEW, pick_many2one("template_id", "مدنية"),
                                            pick_many2one("legal_company_id", "دجلة"),
                                            fill(".modal div[name='opponent_name'] input", "شركة الفرات للتجهيزات"))),
        ("lawyer_quick_create_fee_agreement", seq(MY_DAY, NEW, pick_many2one("template_id", "رأي"),
                                                  pick_many2one("legal_company_id", "دجلة"),
                                                  click(".modal div[name='fee_agreement'] input[data-value='existing']"),
                                                  click(".o_ldm_qc_more .o_ldm_more_toggle_btn"))),
        ("lawyer_palette_search", seq(MY_DAY, palette("دجله"))),
        ("lawyer_palette_numbers", seq(MY_DAY, palette("#1834"))),
        ("lawyer_dossier", goto(f"/odoo/legal-clients/{ids['dijla']}", ".o_ldm_bodies")),
        ("lawyer_agenda", goto("/odoo/legal-agenda", ".o_ldm_agenda")),
        ("lawyer_matters_list", goto("/odoo/matters", ".o_list_view")),
    ],
    "ali": [
        ("clerk_my_day", MY_DAY),
        ("clerk_cockpit_government", matter("tax")),
        ("clerk_cockpit_steps", seq(matter("tax"), click(".o_notebook .nav-link[name='steps']", ".o_ldm_steps"),
                                    scroll_to(".o_notebook"))),
        ("clerk_agenda", goto("/odoo/legal-agenda", ".o_ldm_agenda")),
    ],
    "hussein": [
        ("approver_my_day", MY_DAY),
        ("approver_inbox", goto("/odoo/action-legal_department_management.action_legal_task_to_approve",
                                ".o_ldm_approvals")),
        ("approver_inbox_preview", seq(goto("/odoo/action-legal_department_management.action_legal_task_to_approve",
                                            ".o_ldm_approvals .o_data_row"),
                                       click(".o_ldm_approvals .o_data_row:first-child td[name='display_name']",
                                             ".o_ldm_preview_title"))),
        ("approver_cockpit_banner", matter("amend")),
    ],
    "sara": [
        ("manager_my_day", MY_DAY),
        ("manager_my_day_everyone", seq(MY_DAY, click(".o_ldm_md_scope:last-child", ".o_ldm_my_day[data-scope='all']"))),
        ("manager_handover", seq(goto("/odoo/action-legal_department_management.action_legal_handover_wizard",
                                      ".modal .o_form_view"),
                                 pick_many2one("from_user_id", "زينب"), pick_many2one("to_user_id", "كريم"))),
        ("manager_cockpit_lawsuit", matter("suit")),
    ],
    "mustafa": [
        ("auditor_my_day", MY_DAY),
        ("auditor_cockpit_lawsuit", matter("suit")),
        ("auditor_cockpit_government", seq(matter("tax"), click(".o_notebook .nav-link[name='documents']",
                                                                ".o_ldm_documents"),
                                           scroll_to(".o_notebook"))),
        ("auditor_dossier", goto(f"/odoo/legal-clients/{ids['dijla']}", ".o_ldm_bodies")),
        ("auditor_agenda", goto("/odoo/legal-agenda", ".o_ldm_agenda")),
    ],
}
MOBILE = {
    "zainab": ["lawyer_my_day", "lawyer_cockpit_lawsuit", "lawyer_quick_create_lawsuit", "lawyer_agenda",
               "lawyer_dossier"],
    "ali": ["clerk_my_day", "clerk_cockpit_government", "clerk_cockpit_steps", "clerk_agenda"],
    "hussein": ["approver_my_day", "approver_inbox_preview", "approver_cockpit_banner"],
    "sara": ["manager_my_day", "manager_handover"],
    "mustafa": ["auditor_my_day"],
}

only = [x for x in a.only.split(",") if x]
all_rows = []
with sync_playwright() as p:
    for login, steps in FLOWS.items():
        if only and login not in only:
            continue
        if mobile:
            wanted = MOBILE.get(login, [])
            steps = [s for s in steps if s[0] in wanted]
        if steps:
            all_rows += run_user(p, login, steps)
metrics = os.path.join(a.out, f"{a.prefix}flows_metrics.json")
json.dump(all_rows, open(metrics, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
bad = [r for r in all_rows if r.get("failed") or r.get("error_dialog") or r["page_errors"]]
print(f"{len(all_rows)} screens, {len(bad)} with failures")
sys.exit(1 if bad else 0)

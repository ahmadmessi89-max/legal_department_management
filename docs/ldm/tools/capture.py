"""Screen capture harness for legal_department_management.

Usage:
    py -3.11 docs/ldm/tools/capture.py --base http://127.0.0.1:8095 --db ldm_pro \
        --login admin --password admin --out docs/ldm/evidence/<round> \
        --screens screens.json [--width 1440 --height 900] [--lang ar_001]

screens.json is a list of {"name": "...", "path": "/odoo/action-...", "wait": "css selector",
"clicks": ["css", ...] (optional), "full": true}.  Each screen yields <name>.png and one row in
metrics.json with console errors, page errors and whether an Odoo error dialog was open.
Waits on selectors, never on networkidle: the bus keeps a long-poll open forever.
"""
import argparse, json, os, sys, time
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('--base', default='http://127.0.0.1:8095')
ap.add_argument('--db', required=True)
ap.add_argument('--login', default='admin')
ap.add_argument('--password', default='admin')
ap.add_argument('--out', required=True)
ap.add_argument('--screens', required=True)
ap.add_argument('--width', type=int, default=1440)
ap.add_argument('--height', type=int, default=900)
ap.add_argument('--prefix', default='')
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
screens = json.load(open(a.screens, encoding='utf-8'))
rows = []
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': a.width, 'height': a.height}, locale='ar-IQ')
    page = ctx.new_page()
    console, perr = [], []
    page.on('console', lambda m: console.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: perr.append(str(e)))
    page.goto(f"{a.base}/web/login?db={a.db}")
    page.fill('input[name=login]', a.login)
    page.fill('input[name=password]', a.password)
    page.click('button[type=submit]')
    page.wait_for_selector('.o_main_navbar', timeout=60000)
    for s in screens:
        console.clear(); perr.clear()
        row = {'name': s['name'], 'path': s.get('path')}
        try:
            if s.get('path'):
                page.goto(a.base + s['path'])
            page.wait_for_selector(s.get('wait', '.o_action_manager > *'), timeout=30000)
            for c in s.get('clicks', []):
                page.click(c, timeout=15000)
                time.sleep(0.8)
            time.sleep(s.get('settle', 1.2))
            row['error_dialog'] = page.locator('.o_error_dialog, .o_dialog .modal-title:has-text("Error")').count() > 0
            row['height'] = page.evaluate('document.scrollingElement.scrollHeight')
            fn = os.path.join(a.out, f"{a.prefix}{s['name']}.png")
            page.screenshot(path=fn, full_page=s.get('full', True))
            row['shot'] = fn
        except Exception as e:  # a failed navigation is reported, never presented as evidence
            row['failed'] = str(e)[:500]
        row['console_errors'] = list(console)
        row['page_errors'] = list(perr)
        rows.append(row)
        print(('FAIL ' if row.get('failed') or row.get('error_dialog') or perr else 'ok   ') + s['name'], flush=True)
    b.close()
json.dump(rows, open(os.path.join(a.out, f'{a.prefix}metrics.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
bad = [r for r in rows if r.get('failed') or r.get('error_dialog') or r['page_errors']]
print(f"{len(rows)} screens, {len(bad)} with failures")
sys.exit(1 if bad else 0)

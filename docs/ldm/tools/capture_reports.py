"""Screenshot the module's reports rendered as HTML (this machine has no
wkhtmltopdf, so PDFs cannot be checked here; the HTML is what the PDF is
printed from).

  py -3.11 docs/ldm/tools/capture_reports.py --db ldm_pro --out docs/ldm/evidence/<round> \
      [--login manager] report_name:ids [report_name:ids ...]

Each argument is a report's technical name and the record ids to print,
e.g. legal_department_management.report_legal_task_template:17
"""
import argparse
import os
import time

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:8110")
ap.add_argument("--db", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--login", default="manager")
ap.add_argument("--lang", default="")
ap.add_argument("--files", nargs="*", default=[], help="HTML files written by render_reports.py")
ap.add_argument("reports", nargs="*")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
if a.files:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1000, "height": 1400})
        for path in a.files:
            page.goto("file:///" + os.path.abspath(path).replace(os.sep, "/"))
            time.sleep(1.5)
            shot = os.path.join(a.out, os.path.splitext(os.path.basename(path))[0] + ".png")
            page.screenshot(path=shot, full_page=True)
            print("saved", shot)
        browser.close()
    raise SystemExit(0)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1000, "height": 1400})
    page.goto(f"{a.base}/web/login?db={a.db}")
    page.fill("input[name=login]", a.login)
    page.fill("input[name=password]", a.login)
    page.click("button[type=submit]")
    page.wait_for_selector(".o_main_navbar", timeout=60000)
    for spec in a.reports:
        name, ids = spec.split(":")
        url = f"{a.base}/report/html/{name}/{ids}"
        if a.lang:
            url += f"?context=%7B%22lang%22%3A%22{a.lang}%22%7D"
        page.goto(url)
        time.sleep(1.5)
        short = name.split(".")[-1]
        path = os.path.join(a.out, f"report_{short}_{ids.replace(',', '-')}{'_' + a.lang[:2] if a.lang else ''}.png")
        page.screenshot(path=path, full_page=True)
        print("saved", path)
    browser.close()

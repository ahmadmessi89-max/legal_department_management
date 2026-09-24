"""Journey J1 on a phone (390 x 844): a clerk logs a counter visit with a fee,
a receipt number and a photo of the receipt, counting every tap.

    py -3.11 docs/ldm/evidence/03-gov/j1_phone_visit.py --base http://127.0.0.1:8102 --db ldm_g \
        --login gov_clerk --password gov_clerk --matter <id>

A tap is a click or a touch; typing into a field that was just tapped is not a
tap. Opening the matter counts as one tap (the clerk taps its row on My Day or
in the list). Writes m_j1_*.png beside this script and j1_result.json.
"""
import argparse
import base64
import json
import os
import time

from playwright.sync_api import sync_playwright

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:8102")
ap.add_argument("--db", required=True)
ap.add_argument("--login", required=True)
ap.add_argument("--password", required=True)
ap.add_argument("--matter", required=True)
ap.add_argument("--fee", default="15000")
ap.add_argument("--receipt", default="R-2026-4410")
a = ap.parse_args()
out = os.path.dirname(os.path.abspath(__file__))
taps = []
errors = []


def shot(page, name):
    page.screenshot(path=os.path.join(out, f"m_j1_{name}.png"), full_page=False)


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="ar-IQ", is_mobile=True,
                                  has_touch=True, device_scale_factor=2)
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{a.base}/web/login?db={a.db}")
    page.fill("input[name=login]", a.login)
    page.fill("input[name=password]", a.password)
    page.click("button[type=submit]")
    page.wait_for_selector(".o_main_navbar", timeout=60000)

    page.goto(f"{a.base}/odoo/matters/{a.matter}")
    taps.append("open the matter")
    page.wait_for_selector(".o_form_view")
    time.sleep(1.5)
    shot(page, "1_matter")

    button = page.locator(".o_field_widget[name=step_ids] button[name=action_ldm_log_visit]").first
    button.scroll_into_view_if_needed()
    button.click()
    taps.append("Log visit")
    page.wait_for_selector(".modal .o_form_view")
    time.sleep(1.0)
    shot(page, "2_dialog")

    fee = page.locator(".modal div[name=fee_amount] input")
    fee.click()
    taps.append("fee")
    fee.fill(a.fee)
    receipt = page.locator(".modal div[name=receipt_number] input")
    receipt.click()
    taps.append("receipt number")
    receipt.fill(a.receipt)
    with page.expect_file_chooser() as chooser:
        page.locator(".modal div[name=photo] .o_select_file_button, .modal div[name=photo] img").first.click()
    taps.append("photo of the receipt")
    chooser.value.set_files({"name": "receipt.png", "mimeType": "image/png", "buffer": PNG})
    time.sleep(1.0)
    shot(page, "3_filled")

    page.locator(".modal button[name=action_confirm]").click()
    taps.append("Save visit")
    page.wait_for_selector(".modal", state="detached", timeout=15000)
    time.sleep(1.5)
    shot(page, "4_saved")
    body = page.inner_text(".o_form_view")
    browser.close()

result = {
    "taps": len(taps),
    "tap_list": taps,
    "within_budget": len(taps) <= 6,
    "receipt_in_history": a.receipt in body,
    "page_errors": errors,
}
with open(os.path.join(out, "j1_result.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print(json.dumps(result, ensure_ascii=False))

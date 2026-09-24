import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

/**
 * The vitals strip and the next-step card render the `ldm_cockpit` payload
 * the server composes; the payload is fed directly here.
 */
class LegalTask extends models.Model {
    _name = "legal.task";

    name = fields.Char();
    ldm_cockpit = fields.Json();

    _records = [
        {
            id: 1,
            name: "Supply contract claim",
            ldm_cockpit: {
                kind: "litigation",
                state: "in_progress",
                read_only: false,
                closed: false,
                vitals: [
                    { key: "next", label: "Next date", date: false, days: null, hint: "", tab: false },
                    { key: "sessions", label: "Sessions", value: "1 held of 2", tab: "sessions" },
                    { key: "documents", label: "Documents", value: "4 of 6", tone: "warning", tab: "documents" },
                    { key: "expenses", label: "Expenses", amount: 500000, currency_id: false, tab: "money" },
                    { key: "age", label: "In this status", days: 6, hint: "In progress", tab: false },
                ],
                next: { kind: "hearing", id: 5, label: "Court session at Karkh", date: false, can_act: true },
                approval: false,
                phases: [],
            },
        },
        {
            id: 2,
            name: "Waiting for approval",
            ldm_cockpit: {
                kind: "corporate",
                state: "draft",
                read_only: false,
                vitals: [],
                next: false,
                approval: { state: "to_approve", state_label: "Awaiting approval", requested_by: "Zainab",
                            can_decide: true, can_request: false, since: false },
                phases: [],
            },
        },
    ];
}

// The module depends on mail: users, partners and the mail models are mocked.
defineMailModels();
defineModels([LegalTask]);

const ARCH = `
    <form>
        <sheet>
            <widget name="ldm_next_step"/>
            <widget name="ldm_matter_vitals"/>
            <notebook>
                <page name="steps" string="Steps"><field name="name"/></page>
                <page name="documents" string="Documents"><div class="o_docs_page">Documents page</div></page>
            </notebook>
        </sheet>
    </form>`;

test("draws one vital per fact, the largest text is words", async () => {
    await mountView({ type: "form", resModel: "legal.task", resId: 1, arch: ARCH });
    expect(".o_ldm_vital").toHaveCount(5);
    expect(".o_ldm_vital_documents .o_ldm_vital_value").toHaveText("4 of 6");
    expect(".o_ldm_vital_documents .o_ldm_vital_value").toHaveClass("o_ldm_text_warning");
    // Whole dinars: no fils after the amount.
    expect(".o_ldm_vital_expenses .o_ldm_vital_value").toHaveText("500,000");
    expect(".o_ldm_vital_age .o_ldm_vital_value").toHaveText("6 days");
    expect(".o_ldm_vital_next .o_ldm_vital_value").toHaveText("Nothing dated");
});

test("a vital opens the tab that holds its detail", async () => {
    await mountView({ type: "form", resModel: "legal.task", resId: 1, arch: ARCH });
    expect(".o_docs_page").toHaveCount(0);
    await click(".o_ldm_vital_documents");
    await animationFrame();
    expect(".o_docs_page").toHaveCount(1);
});

test("the next-step card offers the session outcome", async () => {
    await mountView({ type: "form", resModel: "legal.task", resId: 1, arch: ARCH });
    expect(".o_ldm_next_hearing .o_ldm_next_label").toHaveText("Court session at Karkh");
    expect(".o_ldm_next_hearing .o_ldm_action_primary").toHaveCount(1);
    expect(".o_ldm_approval").toHaveCount(0);
});

test("while waiting for approval the banner replaces the card", async () => {
    await mountView({ type: "form", resModel: "legal.task", resId: 2, arch: ARCH });
    expect(".o_ldm_approval_to_approve").toHaveCount(1);
    expect(".o_ldm_next").toHaveCount(0);
    expect(".o_ldm_approve").toHaveCount(1);
    expect(".o_ldm_vital").toHaveCount(0);
});

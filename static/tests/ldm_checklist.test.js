import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, MockServer, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

/**
 * The step checklist ticks a step in one click and offers Undo. The server
 * decides what the tick does (here: a paid visit books expense 7); these tests
 * check the part that lives in the browser: the click, the reload, the Undo
 * button and the ids it sends back.
 */
class LegalTask extends models.Model {
    _name = "legal.task";

    name = fields.Char();
    state = fields.Selection({
        selection: [
            ["in_progress", "In progress"],
            ["done", "Done"],
        ],
    });
    step_ids = fields.One2many({ relation: "legal.task.step", relation_field: "task_id" });

    _records = [
        { id: 1, name: "Tax clearance", state: "in_progress", step_ids: [11, 12] },
        { id: 2, name: "Closed file", state: "done", step_ids: [13, 14] },
    ];
}

class LegalTaskStep extends models.Model {
    _name = "legal.task.step";

    name = fields.Char();
    task_id = fields.Many2one({ relation: "legal.task" });
    state = fields.Selection({
        selection: [
            ["todo", "To do"],
            ["done", "Done"],
            ["skipped", "Skipped"],
        ],
    });
    date_due = fields.Date();
    is_visit = fields.Boolean();

    _records = [
        { id: 11, name: "Collect the documents", task_id: 1, state: "todo", date_due: "2026-09-20" },
        { id: 12, name: "Pay the fee at the counter", task_id: 1, state: "todo", is_visit: true },
        { id: 13, name: "Submit the file", task_id: 2, state: "done" },
        { id: 14, name: "Collect the result", task_id: 2, state: "todo" },
    ];
}

defineModels([LegalTask, LegalTaskStep]);

const ARCH = `
    <form>
        <field name="state" invisible="1"/>
        <field name="step_ids" widget="ldm_step_checklist">
            <list>
                <field name="name"/>
                <field name="state"/>
                <field name="date_due"/>
                <field name="is_visit"/>
            </list>
        </field>
    </form>`;

test("draws one checkbox row per step, with the visit chip and a meter", async () => {
    await mountView({ type: "form", resModel: "legal.task", resId: 1, arch: ARCH });
    expect(".o_ldm_check_row").toHaveCount(2);
    expect(".o_ldm_check_target[role='checkbox']").toHaveCount(2);
    expect(".o_ldm_check_row:eq(1) .o_ldm_pill").toHaveCount(1);
    expect(".o_ldm_checklist_meter").toHaveText("0 / 2");
    // A counter visit offers "Log visit" beside the tick.
    expect(".o_ldm_check_row:eq(1) .o_ldm_check_tools .o_ldm_action").toHaveCount(1);
});

test("one click ticks the step, and Undo sends back the expense it created", async () => {
    onRpc("legal.task.step", "action_ldm_toggle_done", ({ args }) => {
        expect.step(`tick ${args[0][0]}`);
        MockServer.env["legal.task.step"].write(args[0], { state: "done" });
        return { state: "done", expense_ids: [7], message: "Done." };
    });
    onRpc("legal.task.step", "action_ldm_undo_done", ({ args, kwargs }) => {
        expect.step(`undo ${args[0][0]} ${JSON.stringify(kwargs.expense_ids)}`);
        MockServer.env["legal.task.step"].write(args[0], { state: "todo" });
        return true;
    });
    await mountView({ type: "form", resModel: "legal.task", resId: 1, arch: ARCH });

    await click(".o_ldm_check_row:eq(1) .o_ldm_check_target");
    await animationFrame();
    expect.verifySteps(["tick 12"]);
    expect(".o_ldm_check_row:eq(1)").toHaveClass("o_ldm_check_done");
    expect(".o_ldm_check_row:eq(1) .o_ldm_check_target").toHaveAttribute("aria-checked", "true");
    expect(".o_ldm_checklist_meter").toHaveText("1 / 2");

    // The notification offers Undo for a few seconds.
    expect(".o_notification_buttons button").toHaveCount(1);
    await click(".o_notification_buttons button");
    await animationFrame();
    expect.verifySteps(["undo 12 [7]"]);
    expect(".o_ldm_check_row:eq(1)").not.toHaveClass("o_ldm_check_done");
    expect(".o_ldm_checklist_meter").toHaveText("0 / 2");
});

test("a closed matter's checklist cannot be ticked", async () => {
    await mountView({ type: "form", resModel: "legal.task", resId: 2, arch: ARCH });
    expect(".o_ldm_check_target:disabled").toHaveCount(2);
    expect(".o_ldm_checklist_foot").toHaveCount(0);
});

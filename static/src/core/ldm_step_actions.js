import { _t } from "@web/core/l10n/translation";

/**
 * One-click step completion with Undo, shared by My Day, the next-step card
 * and the step checklist, so the three behave identically (SPEC 5.9, G4).
 *
 * The server decides everything: whether the user may tick, whether a paid
 * visit books an expense, which expense Undo may remove. The browser only
 * offers the Undo for six seconds.
 */
export const UNDO_DELAY = 6000;

export async function toggleStep({ orm, notification }, stepId, reload) {
    const result = await orm.call("legal.task.step", "action_ldm_toggle_done", [[stepId]]);
    await reload();
    if (result && result.state === "done") {
        const close = notification.add(result.message, {
            type: "success",
            autocloseDelay: UNDO_DELAY,
            buttons: [
                {
                    name: _t("Undo"),
                    primary: true,
                    onClick: async () => {
                        close();
                        await orm.call("legal.task.step", "action_ldm_undo_done", [[stepId]], {
                            expense_ids: result.expense_ids || [],
                        });
                        await reload();
                    },
                },
            ],
        });
    } else if (result && result.message) {
        notification.add(result.message, { type: "info", autocloseDelay: 3000 });
    }
    return result;
}

/** Run a server method that returns a window action, and reload when it closes. */
export async function runRecordAction({ orm, action }, model, method, resId, reload) {
    const result = await orm.call(model, method, [[resId]]);
    if (result && typeof result === "object" && result.type) {
        await action.doAction(result, { onClose: () => reload() });
    } else {
        await reload();
    }
    return result;
}

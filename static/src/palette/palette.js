import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { DefaultCommandItem } from "@web/core/commands/command_palette";

import { LdmIcon } from "../core/ldm_icon";

/**
 * The legal layer of Odoo's command palette (Ctrl+K, SPEC 5.9).
 *
 *  - typing in the palette also finds matters, clients and bodies (Arabic
 *    spellings folded on the server, record rules applied as the reader);
 *  - "#" searches numbers only: matter, court case, body reference, receipt
 *    and letter numbers; an empty "#" lists recent matters;
 *  - commands: "New matter" (Alt+Shift+N) and "My Day" everywhere, and
 *    "Record session outcome" (Alt+Shift+H) on an open matter (registered by
 *    the matter form).
 */

const LEGAL_GROUPS = [
    "legal_department_management.group_ldm_clerk",
    "legal_department_management.group_ldm_auditor",
    "legal_department_management.group_ldm_billing_user",
];

let accessPromise = null;
/** Only people with a legal role search legal records from the palette. */
function hasLegalAccess() {
    if (!accessPromise) {
        accessPromise = Promise.all(LEGAL_GROUPS.map((group) => user.hasGroup(group))).then((answers) =>
            answers.some(Boolean)
        );
    }
    return accessPromise;
}

export class LdmCommandItem extends Component {
    static template = "legal_department_management.CommandItem";
    static components = { LdmIcon };
    static props = {
        ...DefaultCommandItem.props,
        icon: { type: String, optional: true },
        number: { type: String, optional: true },
        title: { type: String, optional: true },
        line: { type: String, optional: true },
        matched: { type: String, optional: true },
    };
}

const commandSetupRegistry = registry.category("command_setup");
const commandCategoryRegistry = registry.category("command_categories");
const commandProviderRegistry = registry.category("command_provider");

commandSetupRegistry.add("#", {
    debounceDelay: 200,
    emptyMessage: _t("No matter has this number."),
    name: _t("matter numbers"),
    placeholder: _t("Matter, court case, receipt or letter number…"),
});

commandCategoryRegistry.add("ldm", { name: _t("Legal") }, { sequence: 5 });
commandCategoryRegistry.add("ldm_numbers", { namespace: "#", name: _t("Matters") }, { sequence: 10 });
commandCategoryRegistry.add("ldm_matters", { name: _t("Matters") }, { sequence: 70 });
commandCategoryRegistry.add("ldm_clients", { name: _t("Clients") }, { sequence: 71 });
commandCategoryRegistry.add("ldm_bodies", { name: _t("Bodies and courts") }, { sequence: 72 });

let searchSequence = 0;

function openRecord(env, model, id) {
    return env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: model,
        res_id: id,
        views: [[false, "form"]],
        target: "current",
    });
}

function matterCommands(env, matters, category, searchValue) {
    return matters.map((matter) => {
        let name = [matter.number, matter.title, matter.line, matter.matched].filter(Boolean).join(" · ");
        // The palette filters its default results by the command's name. The
        // server already matched Arabic spellings the browser cannot fold
        // (hamza, taa marbuta...), so the typed text is kept in the name to
        // let those matches through; the row itself shows the real fields.
        if (searchValue) {
            name = `${name} ${searchValue}`;
        }
        return {
            Component: LdmCommandItem,
            action: () => openRecord(env, "legal.task", matter.id),
            category,
            name,
            href: `/odoo/matters/${matter.id}`,
            props: {
                icon: "folder-open",
                number: matter.number,
                title: matter.title,
                line: [matter.line, matter.state_label].filter(Boolean).join(" · "),
                matched: matter.matched || "",
            },
        };
    });
}

async function search(env, searchValue, numbersOnly) {
    if (!(await hasLegalAccess())) {
        return null;
    }
    const sequence = ++searchSequence;
    if (!numbersOnly) {
        // The default namespace has no debounce of its own: wait for a pause
        // in typing before asking the server.
        await new Promise((resolve) => setTimeout(resolve, 180));
        if (sequence !== searchSequence) {
            return null;
        }
    }
    return env.services.orm.silent.call("legal.task", "ldm_palette_search", [searchValue], {
        limit: 8,
        numbers_only: numbersOnly,
    });
}

commandProviderRegistry.add("ldm_numbers", {
    namespace: "#",
    async provide(env, options) {
        const result = await search(env, options.searchValue || "", true);
        if (!result) {
            return [];
        }
        return matterCommands(env, result.matters, "ldm_numbers", "");
    },
});

commandProviderRegistry.add("ldm_search", {
    async provide(env, options) {
        const value = (options.searchValue || "").trim();
        if (value.length < 2) {
            return [];
        }
        const result = await search(env, value, false);
        if (!result) {
            return [];
        }
        const commands = matterCommands(env, result.matters, "ldm_matters", value);
        for (const client of result.clients) {
            commands.push({
                Component: LdmCommandItem,
                action: () => openRecord(env, "legal.company", client.id),
                category: "ldm_clients",
                name: `${client.name} ${value}`,
                props: {
                    icon: "briefcase",
                    title: client.name,
                    line: client.open ? _t("%s open matters", client.open) : "",
                },
            });
        }
        for (const body of result.bodies) {
            commands.push({
                Component: LdmCommandItem,
                action: () => openRecord(env, "legal.department", body.id),
                category: "ldm_bodies",
                name: `${body.name} ${body.ministry} ${value}`,
                props: {
                    icon: "building-2",
                    title: body.name,
                    line: body.ministry,
                },
            });
        }
        return commands;
    },
});

/** Commands available on every screen for people who open matters. */
export const ldmCommandsService = {
    dependencies: ["command", "action"],
    async start(env, { command, action }) {
        const canCreate = await user.hasGroup("legal_department_management.group_ldm_clerk");
        if (!canCreate) {
            return;
        }
        command.add(
            _t("New matter"),
            () => action.doAction("legal_department_management.action_legal_task_create_wizard"),
            { category: "ldm", global: true, hotkey: "alt+shift+n" }
        );
        command.add(_t("My Day"), () => action.doAction("legal_department_management.action_legal_dashboard"), {
            category: "ldm",
            global: true,
        });
    },
};

registry.category("services").add("ldm_commands", ldmCommandsService);

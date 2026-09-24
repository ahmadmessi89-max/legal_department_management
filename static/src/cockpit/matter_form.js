import { useState, useSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useCommand } from "@web/core/commands/command_hook";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormCompiler } from "@web/views/form/form_compiler";
import { FormRenderer } from "@web/views/form/form_renderer";
import { StatusBarButtons } from "@web/views/form/status_bar_buttons/status_bar_buttons";
import { append, createElement, getTag } from "@web/core/utils/xml";
import { isTextNode } from "@web/views/view_compiler";

/**
 * The matter cockpit (SPEC 5.3, 14.4): the matter form with
 *
 *  - a header that shows at most the one contextual action (Start, Close
 *    matter, Send for approval) and puts every button marked `o_ldm_more`
 *    in a "⋯" menu beside it;
 *  - the «More» group at the bottom collapsible, the choice remembered per
 *    user (`res.users.settings.ldm_show_advanced`);
 *  - "Record session outcome" in the command palette, on Alt+Shift+H;
 *  - New opening the one-step dialog instead of a blank form.
 *
 * The widgets on the sheet (vitals, next step, phase rail, checklists) are
 * registered separately and read the `ldm_cockpit` payload the server
 * composes.
 */

// --------------------------------------------------------------- header
export class LdmStatusBarButtons extends StatusBarButtons {
    static template = "legal_department_management.StatusBarButtons";

    get mainSlotNames() {
        return this.visibleSlotNames.filter((name) => !this.props.slots[name].ldmMore);
    }

    get moreSlotNames() {
        return this.visibleSlotNames.filter((name) => this.props.slots[name].ldmMore);
    }

    get moreLabel() {
        return _t("More actions");
    }
}

export class LdmMatterFormCompiler extends FormCompiler {
    /**
     * Odoo's header, except that each button's slot says whether the button
     * belongs to the overflow menu (class `o_ldm_more`). The source node is
     * checked in the same loop, because a button that is always invisible
     * compiles to nothing and would shift any index-based mapping.
     */
    compileHeader(el, params) {
        const statusBar = createElement("div", {
            "t-att-class": "{ 'shadow-sm': __comp__.state.isStatusbarStickyPinned }",
        });
        statusBar.className = "o_form_statusbar d-flex justify-content-between py-2";
        const buttons = [];
        const others = [];
        for (const child of el.childNodes) {
            // Read the class before compiling: the button compiler strips the
            // attributes it consumes from the source node.
            const more = Boolean(child.nodeType === 1 && child.classList.contains("o_ldm_more"));
            const compiled = this.compileNode(child, params);
            if (!compiled || isTextNode(compiled)) {
                continue;
            }
            if (getTag(child, true) === "field" && !child.classList.contains("btn")) {
                compiled.setAttribute("showTooltip", true);
                others.push(compiled);
            } else {
                if (compiled.tagName === "ViewButton") {
                    compiled.setAttribute("defaultRank", "'btn-secondary'");
                }
                buttons.push({ compiled, more });
            }
        }
        let slotId = 0;
        const statusBarButtons = createElement("StatusBarButtons");
        for (const { compiled, more } of buttons) {
            const slot = createElement("t", {
                "t-set-slot": `button_${slotId++}`,
                isVisible: compiled.getAttribute("t-if") || true,
            });
            if (more) {
                slot.setAttribute("ldmMore", "true");
            }
            append(slot, compiled);
            append(statusBarButtons, slot);
        }
        append(statusBar, statusBarButtons);
        append(statusBar, others);
        return statusBar;
    }
}

export class LdmMatterFormRenderer extends FormRenderer {
    static components = { ...FormRenderer.components, StatusBarButtons: LdmStatusBarButtons };
}

// ------------------------------------------------------------ controller
export class LdmMatterFormController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.ldm = useState({ advanced: Boolean(user.settings && user.settings.ldm_show_advanced) });
        useSubEnv({
            ldmForm: {
                state: this.ldm,
                toggleAdvanced: () => this.toggleAdvanced(),
            },
        });
        useCommand(_t("Record session outcome"), () => this.recordOutcome(), {
            category: "ldm",
            hotkey: "alt+shift+h",
            isAvailable: () => {
                const record = this.model.root;
                return Boolean(record && record.resId && ["litigation", "execution"].includes(record.data.kind));
            },
        });
    }

    get className() {
        const result = super.className;
        result.o_ldm = true;
        result.o_ldm_matter_form = true;
        result.o_ldm_advanced_on = this.ldm.advanced;
        return result;
    }

    async toggleAdvanced() {
        this.ldm.advanced = !this.ldm.advanced;
        try {
            await user.setUserSettings("ldm_show_advanced", this.ldm.advanced);
        } catch {
            // The preference is a convenience: the form works without it.
        }
    }

    async recordOutcome() {
        const record = this.model.root;
        if (!record.resId) {
            return;
        }
        if (record.dirty) {
            const saved = await record.save();
            if (!saved) {
                return;
            }
        }
        const action = await this.orm.call("legal.task", "ldm_palette_record_outcome", [[record.resId]]);
        await this.actionService.doAction(action, { onClose: () => record.load() });
    }

    /** New opens the one-step dialog: a blank matter form saves nothing useful. */
    async create() {
        const dirty = await this.model.root.isDirty();
        if (dirty && !(await this.model.root.save())) {
            return;
        }
        const clientId = this.model.root.data.legal_company_id?.id;
        await this.actionService.doAction("legal_department_management.action_legal_task_create_wizard", {
            additionalContext: clientId ? { default_legal_company_id: clientId } : {},
        });
    }
}

export const ldmMatterFormView = {
    ...formView,
    Controller: LdmMatterFormController,
    Renderer: LdmMatterFormRenderer,
    Compiler: LdmMatterFormCompiler,
};

registry.category("views").add("ldm_matter_form", ldmMatterFormView);


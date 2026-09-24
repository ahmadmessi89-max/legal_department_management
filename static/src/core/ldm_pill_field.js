import { registry } from "@web/core/registry";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { BadgeField, badgeField } from "@web/views/fields/badge/badge_field";
import { LdmIcon } from "./ldm_icon";

/**
 * A status pill in the workspace's language (design-direction.md): the word
 * carries the meaning, a small Lucide icon and the tint repeat it. It reads
 * the same `decoration-*` attributes as Odoo's badge, so a view switches with
 * `widget="ldm_pill"` and keeps its expressions:
 *
 *   danger  -> red, overdue, missed or rejected
 *   warning -> amber, due soon or something missing
 *   success -> green, done, met or received
 *   info    -> blue, waiting on someone else
 *   primary -> ink outline, work in hand
 *   muted   -> grey, closed or not started
 *
 * Values that are officially confirmed (approved, registered, issued, signed,
 * confirmed genuine) are drawn as the violet stamp instead, when the view
 * names them: `options="{'stamp': ['registered', 'issued']}"`. The stamp is
 * the one motif that means "official", so it is never a default.
 */
const TONES = {
    danger: { tone: "danger", icon: "circle-alert" },
    warning: { tone: "warning", icon: "clock" },
    success: { tone: "success", icon: "circle-check" },
    info: { tone: "info", icon: "hourglass" },
    primary: { tone: "primary", icon: "circle-dot" },
    muted: { tone: "muted", icon: "" },
};

export class LdmPillField extends BadgeField {
    static template = "legal_department_management.LdmPillField";
    static components = { LdmIcon };
    static props = {
        ...BadgeField.props,
        stamp: { type: Array, optional: true },
    };

    get isStamp() {
        const value = this.props.record.data[this.props.name];
        const key = Array.isArray(value) ? value[0] : value && typeof value === "object" ? value.id : value;
        return Boolean(this.props.stamp && this.props.stamp.includes(key));
    }

    get pill() {
        const evalContext = this.props.record.evalContextWithVirtualIds;
        for (const decorationName in this.props.decorations) {
            if (TONES[decorationName] && evaluateBooleanExpr(this.props.decorations[decorationName], evalContext)) {
                return TONES[decorationName];
            }
        }
        return TONES.muted;
    }
}

export const ldmPillField = {
    ...badgeField,
    component: LdmPillField,
    // A pill carries an icon and a word: keep its column wide enough when a
    // list shrinks its columns to fit (Odoo's default floor is 80px).
    listViewWidth: [130],
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...badgeField.extractProps(fieldInfo, dynamicInfo),
        stamp: fieldInfo.options.stamp || undefined,
    }),
};

registry.category("fields").add("ldm_pill", ldmPillField);

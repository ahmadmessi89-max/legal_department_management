import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Many2OneField, buildM2OFieldDescription } from "@web/views/fields/many2one/many2one_field";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

import { shortDate } from "../core/ldm_format";
import { LdmIcon } from "../core/ldm_icon";

/**
 * The matter type picker of the New matter dialog (SPEC 5.2): the types the
 * user opened most recently, one click each, above the ordinary search.
 */
export class LdmTemplatePicker extends Many2OneField {
    static template = "legal_department_management.TemplatePicker";
    static props = {
        ...Many2OneField.props,
        recentsField: { type: String, optional: true },
    };

    get recents() {
        const field = this.props.recentsField || "recent_template_ids";
        const value = this.props.record.data[field];
        if (!value || !value.records) {
            return [];
        }
        const current = this.props.record.data[this.props.name];
        return value.records.map((rec) => ({
            id: rec.resId,
            name: rec.data.display_name,
            active: Boolean(current && current.id === rec.resId),
        }));
    }

    get recentLabel() {
        return _t("Recent");
    }

    choose(recent) {
        this.props.record.update({ [this.props.name]: { id: recent.id, display_name: recent.name } });
    }
}

const m2oDescription = buildM2OFieldDescription(LdmTemplatePicker);
registry.category("fields").add("ldm_template_picker", {
    ...m2oDescription,
    displayName: _t("Matter type picker"),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...m2oDescription.extractProps(staticInfo, dynamicInfo),
            recentsField: staticInfo.options.recents_field || "recent_template_ids",
        };
    },
});

/**
 * «More options» in the New matter dialog: a disclosure button, not a
 * checkbox, so the dialog opens with four inputs and nothing else to fill.
 */
export class LdmMoreToggle extends Component {
    static template = "legal_department_management.MoreToggle";
    static components = { LdmIcon };
    static props ={ ...standardWidgetProps, fieldName: { type: String, optional: true } };

    get field() {
        return this.props.fieldName || "show_more";
    }

    get isOpen() {
        return Boolean(this.props.record.data[this.field]);
    }

    get label() {
        return this.isOpen ? _t("Fewer options") : _t("More options: responsible, team, urgency, note");
    }

    toggle() {
        this.props.record.update({ [this.field]: !this.isOpen });
    }
}

registry.category("view_widgets").add("ldm_more_toggle", {
    component: LdmMoreToggle,
    extractProps: ({ options }) => ({ fieldName: options.field || "show_more" }),
});

/**
 * The suggested target date (design direction): the matter type's duration
 * plus the body's usual answer time, in working days, with "Use this date".
 * Arithmetic the reader can check, never presented as a guess.
 */
export class LdmSuggestedDate extends Component {
    static template = "legal_department_management.SuggestedDate";
    static components = { LdmIcon };
    static props = { ...standardWidgetProps };

    get data() {
        return this.props.record.data;
    }

    get visible() {
        const suggested = this.data.suggested_date;
        const current = this.data.key_date;
        return Boolean(suggested) && !(current && current.toISODate() === suggested.toISODate());
    }

    get dateLabel() {
        return this.data.suggested_date ? shortDate(this.data.suggested_date.toISODate()) : "";
    }

    get title() {
        return _t("Suggested target date");
    }

    get useLabel() {
        return _t("Use this date");
    }

    use() {
        this.props.record.update({ key_date: this.data.suggested_date });
    }
}

registry.category("view_widgets").add("ldm_suggested_date", {
    component: LdmSuggestedDate,
    fieldDependencies: [
        { name: "suggested_date", type: "date" },
        { name: "suggested_note", type: "char" },
        { name: "key_date", type: "date" },
    ],
});

/**
 * The matters register: New opens the one-step dialog, never a blank form.
 */
export class LdmMatterListController extends ListController {
    async createRecord() {
        const context = this.model.root.context || {};
        const additionalContext = {};
        if (context.default_legal_company_id) {
            additionalContext.default_legal_company_id = context.default_legal_company_id;
        }
        await this.actionService.doAction("legal_department_management.action_legal_task_create_wizard", {
            additionalContext,
            onClose: () => this.model.load(),
        });
    }
}

registry.category("views").add("ldm_matter_list", {
    ...listView,
    Controller: LdmMatterListController,
});

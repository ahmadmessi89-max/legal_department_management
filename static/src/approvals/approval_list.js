import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

import { formatAmount, relativeDay, shortDate } from "../core/ldm_format";

/**
 * A read-only summary of the selected matter beside the approvals inbox
 * (SPEC 5.4, S7): enough to decide without leaving the list.
 */
export class LdmApprovalPreview extends Component {
    static template = "legal_department_management.ApprovalPreview";
    static props = {
        taskId: { type: Number },
        onApprove: Function,
        onReject: Function,
        onOpen: Function,
        onClose: Function,
    };

    static labels = {
        loading: _t("Loading the matter…"),
        client: _t("Client"),
        type: _t("Type"),
        body: _t("Body or court"),
        responsible: _t("Responsible"),
        requested: _t("Requested by"),
        value: _t("Value"),
        target: _t("Target date"),
        steps: _t("What the work will be"),
        noSteps: _t("No steps planned."),
        documents: _t("Documents"),
        approve: _t("Approve"),
        reject: _t("Reject"),
        open: _t("Open the matter"),
        close: _t("Close the preview"),
        urgent: _t("Urgent"),
        confidential: _t("Confidential"),
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ data: null });
        onWillStart(() => this.load(this.props.taskId));
        onWillUpdateProps((next) => {
            if (next.taskId !== this.props.taskId) {
                return this.load(next.taskId);
            }
        });
    }

    get label() {
        return LdmApprovalPreview.labels;
    }

    async load(taskId) {
        this.state.data = null;
        this.state.data = await this.orm.call("legal.task", "ldm_approval_preview", [[taskId]]);
    }

    get facts() {
        const data = this.state.data;
        if (!data) {
            return [];
        }
        const facts = [
            { key: "client", label: this.label.client, value: data.client },
            { key: "type", label: this.label.type, value: data.type },
            { key: "body", label: this.label.body, value: data.body },
            { key: "responsible", label: this.label.responsible, value: data.responsible },
            {
                key: "requested",
                label: this.label.requested,
                value: [data.requested_by, data.since ? relativeDay(data.since).label : ""].filter(Boolean).join(" · "),
            },
            { key: "value", label: this.label.value, value: data.value ? formatAmount(data.value, data.currency_id) : "" },
            { key: "target", label: this.label.target, value: data.due_date ? shortDate(data.due_date) : "" },
        ];
        if (data.documents.total) {
            facts.push({
                key: "documents",
                label: this.label.documents,
                value: _t("%(have)s of %(total)s received", data.documents),
            });
        }
        return facts.filter((fact) => fact.value);
    }

    stepDate(step) {
        return step.date ? shortDate(step.date) : "";
    }
}

export class LdmApprovalListController extends ListController {
    static template = "legal_department_management.ApprovalListView";
    static components = { ...ListController.components, LdmApprovalPreview };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.previewState = useState({ id: null });
    }

    /** A click on a row shows its summary beside the list instead of leaving it. */
    async openRecord(record) {
        this.previewState.id = record.resId;
    }

    closePreview() {
        this.previewState.id = null;
    }

    async openFull(taskId) {
        const activeIds = this.model.root.records.map((rec) => rec.resId);
        this.props.selectRecord(taskId, { activeIds });
    }

    async approve(taskId) {
        await this.orm.call("legal.task", "action_approve", [[taskId]]);
        this.previewState.id = null;
        await this.model.load();
    }

    async reject(taskId) {
        const action = await this.orm.call("legal.task", "action_reject", [[taskId]]);
        await this.actionService.doAction(action, {
            onClose: async () => {
                this.previewState.id = null;
                await this.model.load();
            },
        });
    }
}

registry.category("views").add("ldm_approval_list", {
    ...listView,
    Controller: LdmApprovalListController,
});

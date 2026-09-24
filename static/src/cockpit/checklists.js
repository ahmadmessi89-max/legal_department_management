import { Component, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { checkFileSize } from "@web/core/utils/files";
import { useDropzone } from "@web/core/dropzone/dropzone_hook";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FileModel } from "@web/core/file_viewer/file_model";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";

import { relativeDay, shortDate } from "../core/ldm_format";
import { runRecordAction, toggleStep } from "../core/ldm_step_actions";

function isoOf(value) {
    if (!value) {
        return false;
    }
    return typeof value === "string" ? value : value.toISODate();
}

async function saveFirst(record) {
    if (await record.isDirty()) {
        return record.save();
    }
    return true;
}

function isClosed(record) {
    return ["done", "cancelled"].includes(record.data.state);
}

// ========================================================= step checklist
/**
 * The matter's steps as a checklist (SPEC 14.4, GOV.UK task-list anatomy):
 * the whole row is the target, one click ticks it, and Undo is offered for
 * six seconds. A counter visit also offers "Log visit", which records the
 * receipt, the fee and the photo. Adding or changing a step opens a small
 * dialog; the native list stays in the arch only to say which fields to read.
 */
export class LdmStepChecklist extends Component {
    static template = "legal_department_management.StepChecklist";
    static props = { ...standardFieldProps };

    static labels = {
        title: _t("Steps"),
        empty: _t("No steps yet."),
        emptyHint: _t("Add the first step, or choose a matter type that brings its steps."),
        add: _t("Add a step"),
        edit: _t("Change this step"),
        visit: _t("Log visit"),
        visitChip: _t("Visit"),
        saveFirst: _t("Save the matter before ticking its steps."),
        done: _t("Done"),
        skipped: _t("Skipped"),
        tick: _t("Tick to mark done"),
        untick: _t("Done; click to open it again"),
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ busy: {} });
    }

    get label() {
        return LdmStepChecklist.labels;
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    get canEdit() {
        return !this.props.readonly && !isClosed(this.props.record);
    }

    get rows() {
        return this.list.records.map((rec) => {
            const data = rec.data;
            const due = isoOf(data.date_due);
            const rel = due ? relativeDay(due) : null;
            const done = data.state === "done";
            return {
                id: rec.resId,
                name: data.name,
                state: data.state,
                done,
                skipped: data.state === "skipped",
                visit: Boolean(data.is_visit),
                due: due ? shortDate(due) : "",
                dueLabel: rel && !done ? rel.label : "",
                tone: rel && !done ? rel.tone : "",
                user: data.user_id ? data.user_id.display_name : "",
                body: data.department_id ? data.department_id.display_name : "",
                doneOn: done && data.done_date ? shortDate(isoOf(data.done_date)) : "",
                doneBy: done && data.done_by_id ? data.done_by_id.display_name : "",
                note: data.note || "",
            };
        });
    }

    get progress() {
        const rows = this.rows.filter((row) => !row.skipped);
        return { done: rows.filter((row) => row.done).length, total: rows.length };
    }

    reload() {
        return this.props.record.load();
    }

    services() {
        return { orm: this.orm, action: this.action, notification: this.notification };
    }

    async toggle(row) {
        if (!this.canEdit || row.skipped || this.state.busy[row.id]) {
            return;
        }
        if (!this.props.record.resId) {
            this.notification.add(this.label.saveFirst, { type: "warning" });
            return;
        }
        this.state.busy[row.id] = true;
        try {
            if (await saveFirst(this.props.record)) {
                await toggleStep(this.services(), row.id, () => this.reload());
            }
        } finally {
            this.state.busy[row.id] = false;
        }
    }

    async logVisit(row, ev) {
        ev.stopPropagation();
        if (await saveFirst(this.props.record)) {
            await runRecordAction(this.services(), "legal.task.step", "action_ldm_log_visit", row.id, () => this.reload());
        }
    }

    async edit(row, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        if (!(await saveFirst(this.props.record))) {
            return;
        }
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "legal.task.step",
                res_id: row ? row.id : false,
                views: [[false, "form"]],
                target: "new",
                context: { default_task_id: this.props.record.resId },
            },
            { onClose: () => this.reload() }
        );
    }

    add() {
        return this.edit(null);
    }

    rowTitle(row) {
        return row.done ? this.label.untick : this.label.tick;
    }
}

// ===================================================== document checklist
/**
 * The documents to collect (SPEC 14.4): one row per document with its state
 * chip, expiry, the file when there is one, and a place to drop, choose or
 * photograph the file. A file dropped anywhere on the matter is offered to
 * the first document still missing.
 */
export class LdmDocumentChecklist extends Component {
    static template = "legal_department_management.DocumentChecklist";
    static props = { ...standardFieldProps };

    static labels = {
        title: _t("Documents to collect"),
        empty: _t("No documents to collect."),
        emptyHint: _t("A matter type lists the documents its body asks for; they appear here."),
        upload: _t("Choose a file"),
        camera: _t("Take a photo"),
        view: _t("Open the file"),
        drop: _t("Drop the file here"),
        mandatory: _t("Required"),
        expires: _t("Expires %s"),
        saveFirst: _t("Save the matter before adding files."),
        failed: _t("The file could not be uploaded."),
        attachedTo: _t("Attached to “%s”."),
        attachedGeneral: _t("Added to the matter's files."),
        offerTitle: _t("Which document is this?"),
        keepGeneral: _t("Keep it with the matter's files"),
    };

    static tones = {
        missing: "warning",
        received: "info",
        verified: "success",
        expired: "danger",
        not_needed: "",
    };

    setup() {
        this.orm = useService("orm");
        this.http = useService("http");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.fileViewer = useFileViewer();
        this.root = useRef("root");
        this.state = useState({ over: null, busy: false });
        const component = this;
        // A file dropped anywhere on the matter's sheet (not only on a row).
        const sheetRef = {
            get el() {
                const el = component.root.el;
                return el ? el.closest(".o_form_sheet") : null;
            },
        };
        useDropzone(sheetRef, (ev) => this.onSheetDrop(ev), "o_ldm_sheet_dropzone", () => this.canEdit);
    }

    get label() {
        return LdmDocumentChecklist.labels;
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    get canEdit() {
        return !this.props.readonly && !isClosed(this.props.record) && Boolean(this.props.record.resId);
    }

    stateLabel(rec) {
        const field = rec.fields.state;
        const pair = (field && field.selection || []).find(([value]) => value === rec.data.state);
        return pair ? pair[1] : rec.data.state;
    }

    get rows() {
        return this.list.records.map((rec) => {
            const data = rec.data;
            const expiry = isoOf(data.expiry_date);
            return {
                id: rec.resId,
                name: data.name,
                state: data.state,
                stateLabel: this.stateLabel(rec),
                tone: LdmDocumentChecklist.tones[data.state] || "",
                mandatory: Boolean(data.mandatory),
                expiry: expiry ? _t("Expires %s", shortDate(expiry)) : "",
                attachment: data.attachment_id || false,
                missing: ["missing", "expired"].includes(data.state),
                note: data.note || "",
            };
        });
    }

    get meter() {
        const rows = this.rows.filter((row) => row.state !== "not_needed");
        return { have: rows.filter((row) => ["received", "verified"].includes(row.state)).length, total: rows.length };
    }

    // ------------------------------------------------------------ files
    async upload(files, documentId) {
        files = [...(files || [])];
        if (!files.length) {
            return;
        }
        if (!this.props.record.resId) {
            this.notification.add(this.label.saveFirst, { type: "warning" });
            return;
        }
        for (const file of files) {
            if (!checkFileSize(file.size, this.notification)) {
                return;
            }
        }
        if (!(await saveFirst(this.props.record))) {
            return;
        }
        this.state.busy = true;
        try {
            const raw = await this.http.post(
                "/web/binary/upload_attachment",
                { csrf_token: odoo.csrf_token, ufile: files, model: "legal.task", id: this.props.record.resId },
                "text"
            );
            const uploaded = JSON.parse(raw).filter((entry) => !entry.error);
            if (!uploaded.length) {
                this.notification.add(this.label.failed, { type: "danger" });
                return;
            }
            const result = await this.orm.call("legal.task", "ldm_attach_document", [
                [this.props.record.resId],
                documentId || false,
                uploaded.map((entry) => entry.id),
            ]);
            await this.props.record.load();
            this.notification.add(
                result && result.document ? _t("Attached to “%s”.", result.document) : this.label.attachedGeneral,
                { type: "success" }
            );
        } finally {
            this.state.busy = false;
        }
    }

    onInputChange(row, ev) {
        const files = ev.target.files;
        this.upload(files, row.id).finally(() => {
            ev.target.value = "";
        });
    }

    pick(ev) {
        ev.stopPropagation();
        const input = ev.currentTarget.parentElement.querySelector("input[type=file]." + ev.currentTarget.dataset.input);
        if (input) {
            input.click();
        }
    }

    onRowDragOver(row, ev) {
        if (!this.canEdit || !ev.dataTransfer || !ev.dataTransfer.types.includes("Files")) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.state.over = row.id;
    }

    onRowDragLeave(row) {
        if (this.state.over === row.id) {
            this.state.over = null;
        }
    }

    onRowDrop(row, ev) {
        if (!this.canEdit || !ev.dataTransfer) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.state.over = null;
        this.upload(ev.dataTransfer.files, row.id);
    }

    /** A file dropped on the sheet: offer it to the first missing document. */
    onSheetDrop(ev) {
        const files = ev.dataTransfer ? [...ev.dataTransfer.files] : [];
        if (!files.length) {
            return;
        }
        const target = this.rows.find((row) => row.missing);
        if (!target) {
            this.upload(files, false);
            return;
        }
        this.dialog.add(ConfirmationDialog, {
            title: this.label.offerTitle,
            body: _t("Attach “%(file)s” to “%(document)s”, the first document still missing?", {
                file: files[0].name,
                document: target.name,
            }),
            confirmLabel: _t("Attach to “%s”", target.name),
            confirm: () => this.upload(files, target.id),
            cancelLabel: this.label.keepGeneral,
            cancel: () => this.upload(files, false),
        });
    }

    async view(row, ev) {
        ev.stopPropagation();
        const attachmentId = row.attachment.id;
        const [info] = await this.orm.read("ir.attachment", [attachmentId], ["name", "mimetype", "checksum"]);
        const file = Object.assign(new FileModel(), {
            id: attachmentId,
            name: info.name,
            mimetype: info.mimetype,
            checksum: info.checksum,
            type: "binary",
        });
        if (file.isViewable) {
            this.fileViewer.open(file);
        } else {
            window.open(file.downloadUrl, "_blank");
        }
    }
}

const fields = registry.category("fields");
fields.add("ldm_step_checklist", {
    component: LdmStepChecklist,
    displayName: _t("Step checklist"),
    supportedTypes: ["one2many"],
    additionalClasses: ["d-block", "w-100"],
    relatedFields: [
        { name: "name", type: "char" },
        {
            name: "state",
            type: "selection",
            selection: [["todo", _t("To do")], ["done", _t("Done")], ["skipped", _t("Skipped")]],
        },
        { name: "date_due", type: "date" },
        { name: "user_id", type: "many2one", relation: "res.users" },
        { name: "is_visit", type: "boolean" },
        { name: "done_date", type: "date" },
        { name: "done_by_id", type: "many2one", relation: "res.users" },
        { name: "department_id", type: "many2one", relation: "legal.department" },
        { name: "note", type: "char" },
    ],
});
fields.add("ldm_document_checklist", {
    component: LdmDocumentChecklist,
    displayName: _t("Document checklist"),
    supportedTypes: ["one2many"],
    additionalClasses: ["d-block", "w-100"],
    relatedFields: [
        { name: "name", type: "char" },
        {
            name: "state",
            type: "selection",
            selection: [
                ["missing", _t("Missing")],
                ["received", _t("Received")],
                ["verified", _t("Verified")],
                ["expired", _t("Expired")],
                ["not_needed", _t("Not needed")],
            ],
        },
        { name: "mandatory", type: "boolean" },
        { name: "expiry_date", type: "date" },
        { name: "attachment_id", type: "many2one", relation: "ir.attachment" },
        { name: "note", type: "char" },
    ],
});

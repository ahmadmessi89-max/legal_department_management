/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class LegalDashboard extends Component {
    static template = "legal_department_management.LegalDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.allTasksRaw = [];
        this.allCompaniesRaw = [];

        this.state = useState({
            totalCompanies: 0,
            totalTasks: 0,
            inProgressTasks: 0,
            pendingApprovalTasks: 0,
            urgentTasks: 0,
            doneTasks: 0,
            totalExpenses: 0,
            recentTasks: [],
            upcomingSessions: [],
            topDepartments: [],
            myCompanies: [],
            selectedCompanyId: 0,
            selectedCompanyName: "كافة الشركات (عرض شامل)",
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.isLoading = true;
        try {
            // Load ALL companies so that every company appears in the dropdown
            const allCompanies = await this.orm.searchRead(
                "legal.company",
                [],
                ["id", "name", "company_type", "task_count", "pending_tasks_count", "total_expenses", "lawyer_ids"],
                { order: "name asc" }
            );

            this.allCompaniesRaw = allCompanies || [];
            this.state.myCompanies = allCompanies || [];
            this.state.totalCompanies = (allCompanies || []).length;

            // Load all tasks
            const allTasks = await this.orm.searchRead(
                "legal.task",
                [],
                [
                    "id",
                    "name",
                    "task_number",
                    "legal_company_id",
                    "department_id",
                    "lawyer_ids",
                    "state",
                    "approval_state",
                    "is_urgent",
                    "expenses_amount",
                    "session_date",
                    "due_date"
                ],
                { order: "id desc" }
            );

            this.allTasksRaw = allTasks || [];

            // Compute metrics for initial state
            this.applyCompanyFilter(this.state.selectedCompanyId);

        } catch (error) {
            console.error("خطأ في تحميل بيانات لوحة التحكم القانونية:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    onCompanySelectChange(ev) {
        const companyId = parseInt(ev.target.value) || 0;
        this.selectCompany(companyId);
    }

    selectCompany(companyId) {
        this.state.selectedCompanyId = companyId;
        if (companyId === 0) {
            this.state.selectedCompanyName = "كافة الشركات (عرض شامل)";
        } else {
            const comp = this.allCompaniesRaw.find(c => c.id === companyId);
            this.state.selectedCompanyName = comp ? comp.name : "الشركة المحددة";
        }
        this.applyCompanyFilter(companyId);
    }

    applyCompanyFilter(companyId) {
        let tasks = this.allTasksRaw;
        if (companyId && companyId !== 0) {
            tasks = this.allTasksRaw.filter(t => t.legal_company_id && t.legal_company_id[0] === companyId);
        }

        let inProgress = 0;
        let pendingApproval = 0;
        let urgent = 0;
        let done = 0;
        let totalExp = 0;
        const deptCountMap = {};

        const today = new Date().toISOString().split("T")[0];
        const upcomingSessions = [];

        tasks.forEach(task => {
            if (task.state === "in_progress" || task.state === "draft" || task.state === "pending_docs") inProgress += 1;
            if (task.approval_state === "to_approve") pendingApproval += 1;
            if (task.state === "done") done += 1;
            if (task.is_urgent && task.state !== "done" && task.state !== "cancelled") urgent += 1;
            totalExp += task.expenses_amount || 0;

            if (task.department_id && task.department_id[1]) {
                const deptName = task.department_id[1];
                deptCountMap[deptName] = (deptCountMap[deptName] || 0) + 1;
            }

            if (task.session_date && task.session_date >= today && task.state !== "done" && task.state !== "cancelled") {
                upcomingSessions.push(task);
            }
        });

        // Sort top departments
        const sortedDepts = Object.entries(deptCountMap)
            .map(([name, count]) => ({
                name,
                count,
                percentage: Math.min(100, Math.round((count / (tasks.length || 1)) * 100))
            }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 5);

        // Sort upcoming sessions by date
        upcomingSessions.sort((a, b) => (a.session_date > b.session_date ? 1 : -1));

        this.state.totalTasks = tasks.length;
        this.state.inProgressTasks = inProgress;
        this.state.pendingApprovalTasks = pendingApproval;
        this.state.urgentTasks = urgent;
        this.state.doneTasks = done;
        this.state.totalExpenses = totalExp;
        this.state.recentTasks = tasks.slice(0, 8);
        this.state.upcomingSessions = upcomingSessions.slice(0, 5);
        this.state.topDepartments = sortedDepts;
    }

    getCompanyDomain(extraDomain = []) {
        if (this.state.selectedCompanyId && this.state.selectedCompanyId !== 0) {
            return [["legal_company_id", "=", this.state.selectedCompanyId], ...extraDomain];
        }
        return extraDomain;
    }

    openTasksView(domain = []) {
        const fullDomain = this.getCompanyDomain(domain);
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.state.selectedCompanyId ? `قضايا ${this.state.selectedCompanyName}` : "الإجراءات والقضايا القانونية",
            res_model: "legal.task",
            views: [[false, "list"], [false, "kanban"], [false, "form"], [false, "calendar"]],
            domain: fullDomain,
            context: this.state.selectedCompanyId ? { 'default_legal_company_id': this.state.selectedCompanyId } : {},
        });
    }

    openCompaniesView() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "الشركات والكيانات الموكلة",
            res_model: "legal.company",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }

    openPendingApprovals() {
        const domain = this.getCompanyDomain([["approval_state", "=", "to_approve"]]);
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.state.selectedCompanyId ? `معاملات بانتظار الاعتماد - ${this.state.selectedCompanyName}` : "المعاملات بانتظار الاعتماد والموافقة",
            res_model: "legal.task",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: domain,
        });
    }

    openUrgentTasks() {
        const domain = this.getCompanyDomain([["is_urgent", "=", true], ["state", "not in", ["done", "cancelled"]]]);
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.state.selectedCompanyId ? `قضايا عاجلة - ${this.state.selectedCompanyName}` : "القضايا والمعاملات العاجلة",
            res_model: "legal.task",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: domain,
        });
    }

    openDoneTasks() {
        const domain = this.getCompanyDomain([["state", "=", "done"]]);
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.state.selectedCompanyId ? `قضايا منجزة - ${this.state.selectedCompanyName}` : "القضايا المنجزة بنجاح",
            res_model: "legal.task",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: domain,
        });
    }

    openGeneralReport() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "طباعة تقرير الرقابة العامة الشامل",
            res_model: "legal.general.report.wizard",
            views: [[false, "form"]],
            target: "new",
            context: this.state.selectedCompanyId ? { 'default_company_ids': [this.state.selectedCompanyId] } : {},
        });
    }

    createNewTask() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "بدء معاملة / قضية جديدة",
            res_model: "legal.task.create.wizard",
            views: [[false, "form"]],
            target: "new",
            context: this.state.selectedCompanyId ? { 'default_legal_company_id': this.state.selectedCompanyId } : {},
        });
    }

    createNewCompany() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "تسجيل شركة موكلة جديدة",
            res_model: "legal.company",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openTaskRecord(taskId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "legal.task",
            res_id: taskId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openCompanyRecord(companyId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "legal.company",
            res_id: companyId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("legal_dashboard_tag", LegalDashboard);

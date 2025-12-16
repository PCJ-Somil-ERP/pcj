frappe.query_reports["Multi Company Trial Balance"] = {
    filters: [
        {
            fieldname: "fiscal_year",
            label: __("Fiscal Year"),
            fieldtype: "Link",
            options: "Fiscal Year",
            reqd: 1,
            on_change: function () {
                const fy = frappe.query_report.get_filter_value("fiscal_year");
                if (fy) {
                    frappe.db.get_value("Fiscal Year", fy, ["year_start_date", "year_end_date"])
                        .then(r => {
                            if (r.message) {
                                frappe.query_report.set_filter_value("from_date", r.message.year_start_date);
                                frappe.query_report.set_filter_value("to_date", r.message.year_end_date);
                            }
                        });
                }
            }
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1
        }
    ]
};

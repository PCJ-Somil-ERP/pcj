import frappe
from frappe.utils import flt
from erpnext.accounts.report.trial_balance.trial_balance import execute as erpnext_tb_execute
from collections import defaultdict

COMPANIES = [
    "PURANCHAND JAIN & SONS PVT. LTD. (Maharashtra)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Zirakpur)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Alwar)",
    "PURANCHAND JAIN & SONS PVT. LTD. (UP)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Delhi)",
]

VALUE_MAP = {
    "opening_dr": "opening_debit",
    "opening_cr": "opening_credit",
    "debit": "debit",
    "credit": "credit",
    "closing_dr": "closing_debit",
    "closing_cr": "closing_credit",
}

# -------------------------------------------------------
# MAIN API
# -------------------------------------------------------

@frappe.whitelist()
def get_trial_balance(filters=None):
    filters = frappe.parse_json(filters or {})
    validate_filters(filters)

    consolidated_rows = []

    # 1️⃣ CALL STANDARD ERPNext TB (PER COMPANY)
    for company in COMPANIES:
        company_filters = frappe._dict(filters.copy())
        company_filters.company = company

        _, rows = erpnext_tb_execute(company_filters)

        for r in rows:
            if not r or not r.get("account"):
                continue

            consolidated_rows.append({
                "account": r["account"],
                "parent_account": r.get("parent_account"),
                "indent": r.get("indent", 0),
                "company": company,
                "opening_dr": flt(r.get("opening_debit")),
                "opening_cr": flt(r.get("opening_credit")),
                "debit": flt(r.get("debit")),
                "credit": flt(r.get("credit")),
                "closing_dr": flt(r.get("closing_debit")),
                "closing_cr": flt(r.get("closing_credit")),
            })

    # 2️⃣ BUILD TREE (NO ROLL‑UP)
    return build_tree(consolidated_rows)

# -------------------------------------------------------
# VALIDATION
# -------------------------------------------------------

def validate_filters(filters):
    if not filters.get("fiscal_year"):
        frappe.throw("Fiscal Year is required")

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required")

# -------------------------------------------------------
# TREE BUILDING (NO SUMMING)
# -------------------------------------------------------

def build_tree(rows):
    node_map = {}
    roots = []

    # Create nodes
    for r in rows:
        key = (r["company"], r["account"])
        node_map[key] = {
            "account": r["account"],
            "parent_account": r["parent_account"],
            "company": r["company"],
            "indent": r["indent"],
            "opening_dr": r["opening_dr"],
            "opening_cr": r["opening_cr"],
            "debit": r["debit"],
            "credit": r["credit"],
            "closing_dr": r["closing_dr"],
            "closing_cr": r["closing_cr"],
            "children": [],
        }

    # Attach children
    for node in node_map.values():
        parent_key = (node["company"], node["parent_account"])
        if node["parent_account"] and parent_key in node_map:
            node_map[parent_key]["children"].append(node)
        else:
            roots.append(node)

    return roots

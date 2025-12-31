import frappe
from erpnext.accounts.report.trial_balance.trial_balance import execute as erp_tb_execute
from collections import defaultdict

COMPANIES = [
    "PURANCHAND JAIN & SONS PVT. LTD. (Maharashtra)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Zirakpur)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Alwar)",
    "PURANCHAND JAIN & SONS PVT. LTD. (UP)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Delhi)",
]

@frappe.whitelist()
def get_trial_balance(filters=None):
    filters = frappe.parse_json(filters or {})

    if not filters.get("fiscal_year"):
        frappe.throw("Fiscal Year required")

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date & To Date required")

    result = {}

    for company in COMPANIES:
        f = frappe._dict(filters.copy())
        f.company = company

        _, rows = erp_tb_execute(f)

        nodes = {}
        children_map = defaultdict(list)
        roots = []

        for r in rows:
            if not r or not r.get("account"):
                continue

            node = {
                "account": r["account"],
                "parent_account": r.get("parent_account"),
                "company": company,
                "indent": r.get("indent", 0),
                "opening_dr": r.get("opening_debit", 0),
                "opening_cr": r.get("opening_credit", 0),
                "debit": r.get("debit", 0),
                "credit": r.get("credit", 0),
                "closing_dr": r.get("closing_debit", 0),
                "closing_cr": r.get("closing_credit", 0),
                "children": []
            }

            nodes[node["account"]] = node

        for node in nodes.values():
            if node["parent_account"] and node["parent_account"] in nodes:
                nodes[node["parent_account"]]["children"].append(node)
            else:
                roots.append(node)

        result[company] = roots

    return result

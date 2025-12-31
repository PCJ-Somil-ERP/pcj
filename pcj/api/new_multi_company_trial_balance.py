import frappe
from frappe.utils import flt
from erpnext.accounts.report.trial_balance.trial_balance import execute as erpnext_tb_execute
from collections import defaultdict

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------

COMPANIES = [
    "PURANCHAND JAIN & SONS PVT. LTD. (Maharashtra)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Zirakpur)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Alwar)",
    "PURANCHAND JAIN & SONS PVT. LTD. (UP)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Delhi)",
]

VALUE_FIELDS = [
    "opening_dr", "opening_cr",
    "debit", "credit",
    "closing_dr", "closing_cr"
]

# -------------------------------------------------------
# MAIN API
# -------------------------------------------------------

@frappe.whitelist()
def get_trial_balance(filters=None):
    filters = frappe.parse_json(filters or {})
    validate_filters(filters)

    all_rows = []

    # 1️⃣ CALL STANDARD ERPNext TB FOR EACH COMPANY
    for company in COMPANIES:
        company_filters = frappe._dict(filters.copy())
        company_filters.company = company

        _, rows = erpnext_tb_execute(company_filters)

        for r in rows:
            if not r or not r.get("account"):
                continue

            all_rows.append({
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

    # 2️⃣ BUILD COMPANY‑WISE TREES
    trees = build_company_trees(all_rows)

    # 3️⃣ ROLL‑UP CHILD → PARENT (ERP LOGIC)
    for roots in trees.values():
        for root in roots:
            rollup_tree(root)

    # 4️⃣ ADD GRAND TOTAL
    grand_total = calculate_grand_total(trees)

    return {
        "data": trees,
        "grand_total": grand_total
    }

# -------------------------------------------------------
# VALIDATION
# -------------------------------------------------------

def validate_filters(filters):
    if not filters.get("fiscal_year"):
        frappe.throw("Fiscal Year is required")

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required")

# -------------------------------------------------------
# TREE BUILDING
# -------------------------------------------------------

def build_company_trees(rows):
    node_map = {}
    roots_by_company = defaultdict(list)

    # create nodes
    for r in rows:
        key = (r["company"], r["account"])
        node_map[key] = {
            **r,
            "children": []
        }

    # link parent → child
    for node in node_map.values():
        parent_key = (node["company"], node["parent_account"])
        if node["parent_account"] and parent_key in node_map:
            node_map[parent_key]["children"].append(node)
        else:
            roots_by_company[node["company"]].append(node)

    return roots_by_company

# -------------------------------------------------------
# ERP‑STYLE ROLLUP
# -------------------------------------------------------

def rollup_tree(node):
    for child in node["children"]:
        rollup_tree(child)

        for field in VALUE_FIELDS:
            node[field] += child[field]

    # ERP style Dr/Cr netting
    net_pair(node, "opening")
    net_pair(node, "closing")

def net_pair(row, prefix):
    dr = row[f"{prefix}_dr"]
    cr = row[f"{prefix}_cr"]

    if dr >= cr:
        row[f"{prefix}_dr"] = dr - cr
        row[f"{prefix}_cr"] = 0
    else:
        row[f"{prefix}_cr"] = cr - dr
        row[f"{prefix}_dr"] = 0

# -------------------------------------------------------
# GRAND TOTAL
# -------------------------------------------------------

def calculate_grand_total(trees):
    total = {field: 0 for field in VALUE_FIELDS}

    for roots in trees.values():
        for r in roots:
            for field in VALUE_FIELDS:
                total[field] += r[field]

    # net opening & closing (ERP style)
    net_pair(total, "opening")
    net_pair(total, "closing")

    return total

import frappe
from frappe.utils import flt, getdate

COMPANIES = [
    "PURANCHAND JAIN & SONS PVT. LTD. (Maharashtra)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Zirakpur)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Alwar)",
    "PURANCHAND JAIN & SONS PVT. LTD. (UP)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Delhi)",
]

# ---------------- VALIDATION ----------------

def validate_filters(filters):
    if not filters.get("fiscal_year"):
        frappe.throw("Fiscal Year is required")

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required")

    fy = frappe.get_doc("Fiscal Year", filters["fiscal_year"])

    if getdate(filters["from_date"]) < fy.year_start_date or getdate(filters["to_date"]) > fy.year_end_date:
        frappe.throw("Dates must be inside Fiscal Year")

# ---------------- MAIN API ----------------

@frappe.whitelist()
def get_trial_balance(filters=None):
    filters = frappe.parse_json(filters or {})
    validate_filters(filters)

    opening = get_opening_balances(filters)
    period = get_period_balances(filters)
    accounts = get_accounts()

    account_map = {}

    # create nodes
    for acc in accounts:
        key = (acc.name, acc.company)

        opening_bal = flt(opening.get(key, 0))
        debit = flt(period.get(key, {}).get("debit", 0))
        credit = flt(period.get(key, {}).get("credit", 0))
        closing = opening_bal + debit - credit

        account_map[key] = {
            "account": acc.name,
            "parent_account": acc.parent_account,
            "company": acc.company,
            "opening_dr": opening_bal if opening_bal > 0 else 0,
            "opening_cr": abs(opening_bal) if opening_bal < 0 else 0,
            "debit": debit,
            "credit": credit,
            "closing_dr": closing if closing > 0 else 0,
            "closing_cr": abs(closing) if closing < 0 else 0,
            "children": []
        }

    # build tree
    roots = []
    for key, row in account_map.items():
        parent = row["parent_account"]
        company = row["company"]

        parent_key = (parent, company)

        if parent and parent_key in account_map:
            account_map[parent_key]["children"].append(row)
        else:
            roots.append(row)

    # remove empty rows
    return prune_empty(roots)

# ---------------- HELPERS ----------------

def prune_empty(nodes):
    clean = []
    for n in nodes:
        n["children"] = prune_empty(n["children"])
        if (
            n["opening_dr"] or n["opening_cr"]
            or n["debit"] or n["credit"]
            or n["closing_dr"] or n["closing_cr"]
            or n["children"]
        ):
            clean.append(n)
    return clean


def get_accounts():
    return frappe.get_all(
        "Account",
        fields=["name", "parent_account", "company"],
        filters={"company": ["in", COMPANIES]},
        order_by="lft"
    )


def get_opening_balances(filters):
    rows = frappe.db.sql("""
        SELECT account, company, SUM(debit - credit) balance
        FROM `tabGL Entry`
        WHERE company IN %(companies)s
        AND posting_date < %(from_date)s
        AND is_cancelled = 0
        GROUP BY account, company
    """, {
        "companies": tuple(COMPANIES),
        "from_date": filters["from_date"]
    }, as_dict=True)

    return {(r.account, r.company): flt(r.balance) for r in rows}


def get_period_balances(filters):
    rows = frappe.db.sql("""
        SELECT account, company,
               SUM(debit) debit,
               SUM(credit) credit
        FROM `tabGL Entry`
        WHERE company IN %(companies)s
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND is_cancelled = 0
        GROUP BY account, company
    """, {
        "companies": tuple(COMPANIES),
        "from_date": filters["from_date"],
        "to_date": filters["to_date"]
    }, as_dict=True)

    return {
        (r.account, r.company): {
            "debit": flt(r.debit),
            "credit": flt(r.credit)
        } for r in rows
    }

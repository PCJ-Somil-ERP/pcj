import frappe
from frappe.utils import flt, getdate


COMPANIES = [
    "PURANCHAND JAIN & SONS PVT. LTD. (Maharashtra)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Zirakpur)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Alwar)",
    "PURANCHAND JAIN & SONS PVT. LTD. (UP)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Delhi)",
]


# ---------------------------------------------------------------------
# VALIDATIONS
# ---------------------------------------------------------------------
def validate_filters(filters):
    if not filters.get("fiscal_year"):
        frappe.throw("Fiscal Year is required")

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required")

    fy = frappe.get_doc("Fiscal Year", filters["fiscal_year"])

    if getdate(filters["from_date"]) < fy.year_start_date:
        frappe.throw("From Date is before Fiscal Year start")

    if getdate(filters["to_date"]) > fy.year_end_date:
        frappe.throw("To Date is after Fiscal Year end")

    if getdate(filters["from_date"]) > getdate(filters["to_date"]):
        frappe.throw("From Date cannot be after To Date")


# ---------------------------------------------------------------------
# MAIN API
# ---------------------------------------------------------------------
@frappe.whitelist()
def get_trial_balance(filters=None):
    filters = frappe.parse_json(filters or {})
    validate_filters(filters)

    opening_map = get_opening_balances(filters)
    period_map = get_period_balances(filters)
    accounts = get_accounts_tree()

    data = []

    for acc in accounts:
        key = (acc.name, acc.company)

        opening = flt(opening_map.get(key, 0))
        debit = flt(period_map.get(key, {}).get("debit", 0))
        credit = flt(period_map.get(key, {}).get("credit", 0))

        closing = opening + debit - credit

        row = {
            "account": acc.name,
            "parent_account": acc.parent_account,
            "indent": acc.indent,
            "company": acc.company,

            "opening_dr": opening if opening > 0 else 0,
            "opening_cr": abs(opening) if opening < 0 else 0,

            "debit": debit,
            "credit": credit,

            "closing_dr": closing if closing > 0 else 0,
            "closing_cr": abs(closing) if closing < 0 else 0,
        }

        # Same behavior as standard report → skip zero rows
        if (
            row["opening_dr"] or row["opening_cr"] or
            row["debit"] or row["credit"] or
            row["closing_dr"] or row["closing_cr"]
        ):
            data.append(row)

    return {
        "data": data
    }


# ---------------------------------------------------------------------
# OPENING BALANCES (Before From Date)
# ---------------------------------------------------------------------
def get_opening_balances(filters):
    result = frappe.db.sql("""
        SELECT
            account,
            company,
            SUM(debit - credit) AS balance
        FROM `tabGL Entry`
        WHERE company IN %(companies)s
          AND posting_date < %(from_date)s
          AND is_cancelled = 0
        GROUP BY account, company
    """, {
        "companies": tuple(COMPANIES),
        "from_date": filters["from_date"]
    }, as_dict=True)

    return {
        (r.account, r.company): flt(r.balance)
        for r in result
    }


# ---------------------------------------------------------------------
# PERIOD DEBIT / CREDIT
# ---------------------------------------------------------------------
def get_period_balances(filters):
    result = frappe.db.sql("""
        SELECT
            account,
            company,
            SUM(debit) AS debit,
            SUM(credit) AS credit
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
        }
        for r in result
    }


# ---------------------------------------------------------------------
# ACCOUNT TREE (ERPNext Style)
# ---------------------------------------------------------------------
def get_accounts_tree():
    return frappe.get_all(
        "Account",
        fields=[
            "name",
            "parent_account",
            "indent",
            "company"
        ],
        filters={
            "company": ["in", COMPANIES],
            "is_group": ["in", [0, 1]]
        },
        order_by="company, lft"
    )

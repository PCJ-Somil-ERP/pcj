import frappe
from frappe.utils import flt, getdate

COMPANIES = [
    "PURANCHAND JAIN & SONS PVT. LTD. (Maharashtra)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Zirakpur)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Alwar)",
    "PURANCHAND JAIN & SONS PVT. LTD. (UP)",
    "PURANCHAND JAIN & SONS PVT. LTD. (Delhi)",
]

def execute(filters=None):
    filters = frappe._dict(filters or {})

    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data

def validate_filters(filters):
    if not filters.fiscal_year:
        frappe.throw("Fiscal Year is required")

    if not filters.from_date or not filters.to_date:
        frappe.throw("From Date and To Date are required")

    fy = frappe.get_doc("Fiscal Year", filters.fiscal_year)

    if getdate(filters.from_date) < fy.year_start_date or getdate(filters.to_date) > fy.year_end_date:
        frappe.throw("Selected dates must be within Fiscal Year")

    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw("From Date cannot be after To Date")

def get_columns():
    return [
        {"label": "Account", "fieldname": "account", "fieldtype": "Link", "options": "Account", "width": 260},
        {"label": "Opening (Dr)", "fieldname": "opening_dr", "fieldtype": "Currency", "width": 140},
        {"label": "Opening (Cr)", "fieldname": "opening_cr", "fieldtype": "Currency", "width": 140},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency", "width": 140},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency", "width": 140},
        {"label": "Closing (Dr)", "fieldname": "closing_dr", "fieldtype": "Currency", "width": 140},
        {"label": "Closing (Cr)", "fieldname": "closing_cr", "fieldtype": "Currency", "width": 140},
    ]

def get_data(filters):
    opening = get_opening_balances(filters)
    period = get_period_balances(filters)

    accounts = set(opening) | set(period)
    data = []

    for account in sorted(accounts):
        opening_bal = flt(opening.get(account, 0))
        debit = flt(period.get(account, {}).get("debit", 0))
        credit = flt(period.get(account, {}).get("credit", 0))

        closing = opening_bal + debit - credit

        row = {
            "account": account,
            "opening_dr": opening_bal if opening_bal > 0 else 0,
            "opening_cr": abs(opening_bal) if opening_bal < 0 else 0,
            "debit": debit,
            "credit": credit,
            "closing_dr": closing if closing > 0 else 0,
            "closing_cr": abs(closing) if closing < 0 else 0,
        }

        if any(row[key] for key in row if key != "account"):
            data.append(row)

    return data

def get_opening_balances(filters):
    result = frappe.db.sql("""
        SELECT
            account,
            SUM(debit - credit) AS balance
        FROM `tabGL Entry`
        WHERE company IN %(companies)s
        AND posting_date < %(from_date)s
        AND is_cancelled = 0
        GROUP BY account
    """, {
        "companies": COMPANIES,
        "from_date": filters.from_date
    }, as_dict=True)

    return {row.account: flt(row.balance) for row in result}

def get_period_balances(filters):
    result = frappe.db.sql("""
        SELECT
            account,
            SUM(debit) AS debit,
            SUM(credit) AS credit
        FROM `tabGL Entry`
        WHERE company IN %(companies)s
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND is_cancelled = 0
        GROUP BY account
    """, {
        "companies": COMPANIES,
        "from_date": filters.from_date,
        "to_date": filters.to_date
    }, as_dict=True)

    return {
        row.account: {
            "debit": flt(row.debit),
            "credit": flt(row.credit)
        } for row in result
    }

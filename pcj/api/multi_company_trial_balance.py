import frappe
from frappe.utils import flt, getdate

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

    validate_filters(filters)

    opening_map = get_opening_balances(filters)
    period_map = get_period_balances(filters)
    accounts = get_accounts_tree()

    data = []

    for acc in accounts:
        account = acc.name
        company = acc.company

        opening = flt(opening_map.get((account, company), 0))
        debit = flt(period_map.get((account, company), {}).get("debit", 0))
        credit = flt(period_map.get((account, company), {}).get("credit", 0))

        closing = opening + debit - credit

        row = {
            "account": account,
            "parent_account": acc.parent_account,
            "indent": acc.indent,
            "company": company,

            "opening_dr": opening if opening > 0 else 0,
            "opening_cr": abs(opening) if opening < 0 else 0,

            "debit": debit,
            "credit": credit,

            "closing_dr": closing if closing > 0 else 0,
            "closing_cr": abs(closing) if closing < 0 else 0,
        }

        if any([
            row["opening_dr"], row["opening_cr"],
            row["debit"], row["credit"],
            row["closing_dr"], row["closing_cr"]
        ]):
            data.append(row)

    return data

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

def get_accounts_tree():
    return frappe.get_all(
        "Account",
        fields=["name", "parent_account", "indent", "company"],
        filters={"company": ["in", COMPANIES]},
        order_by="lft"
    )

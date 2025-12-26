import frappe
from frappe.utils import flt, getdate

@frappe.whitelist()
def get_trial_balance(filters=None):
    filters = frappe.parse_json(filters or {})

    validate_filters(filters)

    companies = filters.get("companies") or get_all_companies()

    accounts = get_accounts_tree()

    balances = get_gl_balances(filters, companies)

    data = build_tree_data(accounts, balances)

    return {
        "columns": get_columns(),
        "data": data
    }


# ---------------- VALIDATION ----------------

def validate_filters(filters):
    if not filters.get("fiscal_year"):
        frappe.throw("Fiscal Year is required")

    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required")

    fy = frappe.get_doc("Fiscal Year", filters["fiscal_year"])

    if getdate(filters["from_date"]) < fy.year_start_date or getdate(filters["to_date"]) > fy.year_end_date:
        frappe.throw("Dates must be inside Fiscal Year")


# ---------------- ACCOUNTS TREE ----------------

def get_accounts_tree():
    return frappe.db.sql("""
        SELECT
            name, parent_account, lft, rgt
        FROM `tabAccount`
        WHERE is_group = 0
        ORDER BY lft
    """, as_dict=True)


# ---------------- GL BALANCES ----------------

def get_gl_balances(filters, companies):
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
        "companies": tuple(companies),
        "from_date": filters["from_date"],
        "to_date": filters["to_date"]
    }, as_dict=True)

    balances = {}
    for row in result:
        balances.setdefault(row.account, {})
        balances[row.account][row.company] = {
            "debit": flt(row.debit),
            "credit": flt(row.credit)
        }

    return balances


# ---------------- TREE DATA ----------------

def build_tree_data(accounts, balances):
    data = []

    for acc in accounts:
        if acc.name not in balances:
            continue

        for company, vals in balances[acc.name].items():
            row = {
                "account": acc.name,
                "parent_account": acc.parent_account,
                "indent": get_indent(acc),
                "company": company,
                "debit": vals["debit"],
                "credit": vals["credit"],
                "closing": vals["debit"] - vals["credit"]
            }
            data.append(row)

    return data


def get_indent(account):
    return frappe.db.count(
        "Account",
        {"lft": ("<", account.lft), "rgt": (">", account.rgt)}
    )


# ---------------- HELPERS ----------------

def get_all_companies():
    return frappe.get_all("Company", pluck="name")


def get_columns():
    return [
        {"label": "Account", "fieldname": "account", "fieldtype": "Link", "options": "Account"},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company"},
        {"label": "Debit", "fieldname": "debit", "fieldtype": "Currency"},
        {"label": "Credit", "fieldname": "credit", "fieldtype": "Currency"},
        {"label": "Closing", "fieldname": "closing", "fieldtype": "Currency"},
    ]

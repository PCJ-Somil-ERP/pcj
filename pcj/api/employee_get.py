import frappe

@frappe.whitelist(allow_guest=False)
def get_employee(employee_id=None):
    filters = {}
    if employee_id:
        filters["name"] = employee_id

    employees = frappe.get_all(
        "Employee",
        filters=filters,
        fields=[
            "name",
            "employee_name",
            "designation",
            "department",
            "status",
            "company"
        ]
    )
    return employees

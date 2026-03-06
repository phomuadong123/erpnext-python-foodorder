import frappe


@frappe.whitelist()
def create_user(zalo_user_id):

    if not frappe.db.exists("Zalo User Map", {"zalo_user_id": zalo_user_id}):

        doc = frappe.get_doc({
            "doctype": "Zalo User Map",
            "zalo_user_id": zalo_user_id
        })

        doc.insert(ignore_permissions=True)

    return "ok"


@frappe.whitelist()
def create_order(zalo_user_id, item):

    session = frappe.get_all(
        "Lunch Session",
        filters={"status": "Open"},
        fields=["name"],
        limit=1
    )

    if not session:
        return "No active session"

    session_name = session[0]["name"]

    existing = frappe.db.exists(
        "Lunch Order",
        {
            "zalo_user_id": zalo_user_id,
            "lunch_session": session_name
        }
    )

    if existing:
        return "Already voted"

    doc = frappe.get_doc({
        "doctype": "Lunch Order",
        "zalo_user_id": zalo_user_id,
        "lunch_session": session_name,
        "item": item
    })

    doc.insert(ignore_permissions=True)

    return "ok"


@frappe.whitelist()
def get_totals():

    session = frappe.get_all(
        "Lunch Session",
        filters={"status": "Open"},
        fields=["name"],
        limit=1
    )

    if not session:
        return {"ga": 0, "vit": 0}

    session_name = session[0]["name"]

    orders = frappe.get_all(
        "Lunch Order",
        filters={"lunch_session": session_name},
        fields=["item"]
    )

    totals = {"ga": 0, "vit": 0}

    for o in orders:
        if o.item == "ga":
            totals["ga"] += 1
        if o.item == "vit":
            totals["vit"] += 1

    return totals
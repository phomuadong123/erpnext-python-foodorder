from fastapi import FastAPI, Request, Header, HTTPException
import hashlib
import hmac
import json
import requests
import os

app = FastAPI()

# ===============================
# ENVIRONMENT VARIABLES
# ===============================

ZALO_OA_SECRET = os.getenv("ZALO_OA_SECRET")
ZALO_ACCESS_TOKEN = os.getenv("ZALO_ACCESS_TOKEN")

FRAPPE_API_URL = os.getenv("FRAPPE_API_URL")
FRAPPE_API_KEY = os.getenv("FRAPPE_API_KEY")
FRAPPE_API_SECRET = os.getenv("FRAPPE_API_SECRET")


# ===============================
# HELPER: VERIFY SIGNATURE
# ===============================

def verify_signature(raw_body: bytes, signature: str):
    mac = hmac.new(
        ZALO_OA_SECRET.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return mac == signature


# ===============================
# HELPER: SEND MESSAGE TO ZALO
# ===============================

def send_message(user_id, text):

    payload = {
        "recipient": {"user_id": user_id},
        "message": {"text": text}
    }

    headers = {
        "Content-Type": "application/json",
        "access_token": ZALO_ACCESS_TOKEN
    }

    requests.post(
        "https://openapi.zalo.me/v2.0/oa/message",
        json=payload,
        headers=headers
    )


# ===============================
# HELPER: SEND POLL
# ===============================

def send_poll_message(user_id):

    payload = {
        "recipient": {"user_id": user_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": "🍱 Hôm nay bạn ăn gì?",
                    "buttons": [
                        {
                            "title": "🍗 Cơm gà",
                            "type": "message",
                            "payload": "ga"
                        },
                        {
                            "title": "🦆 Cơm vịt",
                            "type": "message",
                            "payload": "vit"
                        }
                    ]
                }
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "access_token": ZALO_ACCESS_TOKEN
    }

    requests.post(
        "https://openapi.zalo.me/v2.0/oa/message",
        json=payload,
        headers=headers
    )


# ===============================
# ERP HELPERS
# ===============================

def frappe_headers():
    return {
        "Authorization": f"token {FRAPPE_API_KEY}:{FRAPPE_API_SECRET}"
    }


def create_user_if_not_exists(zalo_user_id):

    url = f"{FRAPPE_API_URL}/api/method/food_order.api.create_user"

    requests.post(
        url,
        json={"zalo_user_id": zalo_user_id},
        headers=frappe_headers()
    )


def create_order(zalo_user_id, item):

    url = f"{FRAPPE_API_URL}/api/method/food_order.api.create_order"

    requests.post(
        url,
        json={
            "zalo_user_id": zalo_user_id,
            "item": item
        },
        headers=frappe_headers()
    )


def get_totals():

    url = f"{FRAPPE_API_URL}/api/method/food_order.api.get_totals"

    r = requests.get(url, headers=frappe_headers())

    return r.json().get("message", {})


def get_all_users():

    url = f"{FRAPPE_API_URL}/api/resource/Zalo User Map"

    r = requests.get(url, headers=frappe_headers())

    return [u["zalo_user_id"] for u in r.json().get("data", [])]


def broadcast_totals(totals):

    users = get_all_users()

    message = f"""
📊 Cập nhật số lượng hiện tại:

🍗 Cơm gà: {totals.get('ga', 0)}
🦆 Cơm vịt: {totals.get('vit', 0)}
"""

    for user in users:
        send_message(user, message)


# ===============================
# WEBHOOK
# ===============================

@app.post("/webhook/zalo")
async def webhook_zalo(
    request: Request,
    x_zalo_signature: str = Header(None)
):

    raw_body = await request.body()

    if not verify_signature(raw_body, x_zalo_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = json.loads(raw_body)

    print("Webhook received:", data)

    # FOLLOW EVENT
    if data.get("event_name") == "follow":
        user_id = data["follower"]["id"]
        create_user_if_not_exists(user_id)
        send_message(user_id, "👋 Bạn đã đăng ký hệ thống đặt cơm.")

    # MESSAGE EVENT (vote)
    if "message" in data:

        user_id = data["sender"]["id"]
        text = data["message"].get("text")

        if text in ["ga", "vit"]:

            create_order(user_id, text)

            totals = get_totals()

            broadcast_totals(totals)

    return {"status": "ok"}


# ===============================
# ERP TRIGGER ENDPOINT
# ===============================

@app.post("/send-poll")
async def send_poll(request: Request):

    data = await request.json()
    session_id = data.get("session_id")

    print("Trigger poll for session:", session_id)

    users = get_all_users()

    for user in users:
        send_poll_message(user)

    return {"status": "poll sent"}
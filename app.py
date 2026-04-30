#!/usr/bin/env python3
"""ZakaPay API v2 — Port 8080"""

import os, json, hashlib, time, requests
from flask import Flask, request, jsonify
from stellar_sdk import Keypair, Server, TransactionBuilder, Network, Asset

app = Flask(__name__)
HORIZON = "https://horizon-testnet.stellar.org"
FRIENDBOT = "https://friendbot.stellar.org"
NETWORK = Network.TESTNET_NETWORK_PASSPHRASE
DB_FILE = "/data/data/com.termux/files/home/ZakaPay-project/users.json"
stellar = Server(horizon_url=HORIZON)

def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def get_balance(public_key):
    try:
        resp = requests.get(f"{HORIZON}/accounts/{public_key}")
        if resp.status_code == 200:
            return resp.json()["balances"][0]["balance"]
    except:
        pass
    return "0.0000000"

def parse_message():
    if request.content_type and "form" in request.content_type:
        phone = request.values.get("From", "").replace("whatsapp:", "")
        text = request.values.get("Body", "").strip().lower()
        return phone, text
    if request.is_json:
        data = request.get_json()
        if "messages" in data:
            msg = data["messages"][0]
            return msg.get("from", ""), msg.get("text", {}).get("body", "").strip().lower()
        return data.get("from", ""), data.get("text", "").strip().lower()
    return "", ""

def format_reply(phone, text):
    is_twilio = request.content_type and "form" in request.content_type
    if is_twilio:
        try:
            from twilio.twiml.messaging_response import MessagingResponse
            resp = MessagingResponse()
            resp.message(text)
            return str(resp), 200, {"Content-Type": "application/xml"}
        except:
            return text, 200
    return jsonify({"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": text}}), 200

@app.route("/api/v1/ping", methods=["GET"])
def ping():
    return jsonify({"status": "alive", "service": "ZakaPay", "version": "2.0.0", "network": "Stellar Testnet", "message": "Banking without a bank"})

@app.route("/api/v1/webhook/whatsapp", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    phone, text = parse_message()
    if not phone or not text:
        return format_reply("", "No message received.")
    users = load_users()
    reply = ""
    if text in ["hi", "hello", "zaka", "start", "menu"]:
        if phone in users:
            name = users[phone]["name"]
            bal = get_balance(users[phone]["public_key"])
            reply = f"Welcome back, {name}!\n\nBalance: {bal} XLM\n\nCommands:\n*balance* — Check wallet\n*send* — Send money\n*help* — All commands"
        else:
            reply = "Welcome to ZakaPay!\n\nThe fastest way to pay at the Spaza.\n\nTo create your wallet, reply:\n*register your_name 1234*\n\nExample: *register Thabo 1234*"
    elif text.startswith("register"):
        parts = text.split()
        if len(parts) < 3:
            reply = "To register, reply:\n*register your_name 1234*"
        elif phone in users:
            reply = f"Already registered, {users[phone]['name']}! Reply *balance*."
        else:
            name, pin = parts[1].capitalize(), parts[2]
            if len(pin) != 4 or not pin.isdigit():
                reply = "PIN must be 4 digits."
            else:
                kp = Keypair.random()
                users[phone] = {"name": name, "public_key": kp.public_key, "secret_encrypted": kp.secret, "pin_hash": hash_pin(pin), "pin_attempts": 0, "frozen": False, "created_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                save_users(users)
                funded = False
                try:
                    funded = requests.get(FRIENDBOT, params={"addr": kp.public_key}).status_code == 200
                except:
                    pass
                reply = f"Account created!\n\nName: {name}\nWallet: {kp.public_key[:8]}...{kp.public_key[-4:]}\nFunded: {'10,000 XLM' if funded else 'Pending'}\n\nReply *balance* to check your wallet."
    elif text == "balance":
        if phone not in users:
            reply = "No wallet yet. Reply *hi* to get started."
        else:
            user = users[phone]
            bal = get_balance(user["public_key"])
            reply = f"Your ZakaPay Wallet\n\nName: {user['name']}\nBalance: {bal} XLM\nWallet: {user['public_key'][:8]}...{user['public_key'][-4:]}\n\nReply *send* to send money."
    elif text == "send":
        if phone not in users:
            reply = "No wallet yet. Reply *hi* to get started."
        else:
            reply = "To send money, reply:\n*send amount phone pin*\n\nExample: *send 10 +27820000002 1234*\n\nFee: R2.50 per transaction"
    elif text.startswith("send "):
        parts = text.split()
        if len(parts) < 4:
            reply = "Format: *send amount phone pin*\nExample: *send 10 +27820000002 1234*"
        elif phone not in users:
            reply = "No wallet yet. Reply *hi* to get started."
        else:
            amount, recv_phone, pin = parts[1], parts[2], parts[3]
            sender = users[phone]
            if hash_pin(pin) != sender["pin_hash"]:
                reply = "Wrong PIN."
            elif sender["frozen"]:
                reply = "Account frozen."
            elif recv_phone not in users:
                reply = "Recipient not found."
            else:
                receiver = users[recv_phone]
                try:
                    kp = Keypair.from_secret(sender["secret_encrypted"])
                    account = stellar.load_account(kp.public_key)
                    tx = TransactionBuilder(account, NETWORK, 100).add_text_memo(f"ZakaPay:{receiver['name']}").append_payment_op(destination=receiver["public_key"], amount=str(amount), asset=Asset.native()).set_timeout(30).build()
                    tx.sign(kp)
                    resp = stellar.submit_transaction(tx)
                    reply = f"Sent!\n\nAmount: {amount} XLM\nTo: {receiver['name']}\nFee: R2.50\nTx: {resp['hash'][:16]}...\n\nReply *balance* to see your new balance."
                except Exception as e:
                    reply = f"Payment failed: {str(e)[:100]}"
    elif text == "help":
        reply = "ZakaPay Commands\n\n*hi* — Start or menu\n*register name pin* — Create wallet\n*balance* — Check balance\n*send* — Send instructions\n*send amount phone pin* — Send money\n*help* — This message\n\nFee: R2.50 per send\nBanking without a bank."
    else:
        reply = "I didn't understand. Reply *hi* to see what I can do."
    return format_reply(phone, reply)

@app.route("/api/v1/webhook/whatsapp", methods=["GET"])
@app.route("/webhook", methods=["GET"])
def whatsapp_verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == "zakapay_verify_2026":
        return request.args.get("hub.challenge"), 200
    return jsonify({"status": "webhook active"}), 200

if __name__ == "__main__":
    print("=" * 50)
    print("  ZakaPay API v2 — Port 8080")
    print("  Banking without a bank")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=False)

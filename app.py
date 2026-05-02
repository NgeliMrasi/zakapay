#!/usr/bin/env python3
"""
ZakaPay v2.2 — Professional WhatsApp UI with Persistent State
State survives Render free tier spin-downs.
"""

import os
import json
import hashlib
import requests
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from stellar_sdk import Keypair, Server, TransactionBuilder, Network, Asset

app = Flask(__name__)
CORS(app)

HORIZON = "https://horizon-testnet.stellar.org"
NETWORK = Network.TESTNET_NETWORK_PASSPHRASE
DB_FILE = os.environ.get("DB_FILE", "users.json")
ZARC_FILE = os.environ.get("ZARC_FILE", "zarc.json")
STATE_FILE = os.environ.get("STATE_FILE", "user_states.json")
server = Server(horizon_url=HORIZON)


# ─── Persistent State ───

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(states):
    with open(STATE_FILE, "w") as f:
        json.dump(states, f, indent=2)


def get_user_state(phone):
    states = load_state()
    return states.get(phone)


def set_user_state(phone, state):
    states = load_state()
    states[phone] = state
    save_state(states)


def clear_user_state(phone):
    states = load_state()
    states.pop(phone, None)
    save_state(states)


# ─── Data Loading ───

def load_users():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)


def load_zarc():
    try:
        with open(ZARC_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def get_balance(public_key, asset_code="native"):
    try:
        resp = requests.get(f"{HORIZON}/accounts/{public_key}", timeout=10)
        if resp.status_code == 200:
            for bal in resp.json()["balances"]:
                if asset_code == "native" and bal["asset_type"] == "native":
                    return float(bal["balance"])
                elif bal.get("asset_code") == asset_code:
                    return float(bal["balance"])
    except:
        pass
    return 0.0


def get_zarc_balance(public_key):
    zarc = load_zarc()
    if not zarc:
        return 0.0
    try:
        resp = requests.get(f"{HORIZON}/accounts/{public_key}", timeout=10)
        if resp.status_code == 200:
            for bal in resp.json()["balances"]:
                if (bal.get("asset_code") == "ZARC" and
                    bal.get("asset_issuer") == zarc["issuer_public"]):
                    return float(bal["balance"])
    except:
        pass
    return 0.0


def find_user(users, phone):
    clean = phone.replace(" ", "").replace("-", "")
    for p, u in users.items():
        if p == clean:
            return p, u
    return None, None


# ─── Message Formatting ───

def format_menu(user_name):
    return (
        f"Hello {user_name}! Welcome to ZakaPay.\n"
        f"Banking without a bank.\n"
        f"\n"
        f"What would you like to do?\n"
        f"\n"
        f"1. Check Balance\n"
        f"2. Send Money\n"
        f"3. Deposit (Bank \u2192 ZakaPay)\n"
        f"4. Withdraw (ZakaPay \u2192 Bank)\n"
        f"5. Transaction History\n"
        f"6. Help\n"
        f"\n"
        f"Reply with a number (1-6)"
    )


def format_balance(name, zar, xlm):
    return (
        f"Your Balances\n"
        f"\n"
        f"Rands: R{zar:,.2f}\n"
        f"XLM: {xlm:,.2f}\n"
        f"\n"
        f"1 ZARC = R1.00\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_send_prompt():
    return (
        f"Send Money\n"
        f"\n"
        f"Enter amount and phone number:\n"
        f"\n"
        f"Example:\n"
        f"  100 +27820000002\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_send_success(amount, name, phone, bal, tx):
    return (
        f"Sent!\n"
        f"\n"
        f"Amount: R{amount:,.2f}\n"
        f"To: {name}\n"
        f"Phone: {phone}\n"
        f"Your Balance: R{bal:,.2f}\n"
        f"Tx: {tx[:16]}...\n"
        f"\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx}\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_deposit_prompt():
    return (
        f"Deposit (Bank \u2192 ZakaPay)\n"
        f"\n"
        f"Enter the amount:\n"
        f"\n"
        f"Example:\n"
        f"  500\n"
        f"\n"
        f"Maximum: R50,000\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_deposit_success(amount, bal, tx):
    return (
        f"Deposit Successful!\n"
        f"\n"
        f"Amount: R{amount:,.2f}\n"
        f"New Balance: R{bal:,.2f}\n"
        f"Tx: {tx[:16]}...\n"
        f"\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx}\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_withdraw_prompt():
    return (
        f"Withdraw (ZakaPay \u2192 Bank)\n"
        f"\n"
        f"Enter the amount:\n"
        f"\n"
        f"Example:\n"
        f"  500\n"
        f"\n"
        f"Funds arrive in 1-2 business days.\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_withdraw_success(amount, bal, tx):
    return (
        f"Withdrawal Successful!\n"
        f"\n"
        f"Amount: R{amount:,.2f}\n"
        f"New Balance: R{bal:,.2f}\n"
        f"Tx: {tx[:16]}...\n"
        f"\n"
        f"Funds in bank account in 1-2 days.\n"
        f"\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx}\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_help():
    return (
        f"ZakaPay Help\n"
        f"\n"
        f"Menu:\n"
        f"  hi / 0    \u2014 Main menu\n"
        f"  1         \u2014 Check balance\n"
        f"  2         \u2014 Send money\n"
        f"  3         \u2014 Deposit\n"
        f"  4         \u2014 Withdraw\n"
        f"  5         \u2014 History\n"
        f"  6         \u2014 Help\n"
        f"\n"
        f"Quick:\n"
        f"  balance\n"
        f"  send 100 +27xxx\n"
        f"  deposit 500\n"
        f"  withdraw 500\n"
        f"  register Name 1234\n"
        f"\n"
        f"Support: ngeli@zakapay.africa\n"
        f"Website: zakapay.africa\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_welcome():
    return (
        f"Welcome to ZakaPay!\n"
        f"Banking without a bank.\n"
        f"\n"
        f"You don't have a wallet yet.\n"
        f"Create one in 10 seconds:\n"
        f"\n"
        f"Send: register YourName 1234\n"
        f"\n"
        f"Example:\n"
        f"  register Thabo 1234"
    )


def format_registered(name, pk):
    return (
        f"Welcome to ZakaPay, {name}!\n"
        f"\n"
        f"Your wallet is ready.\n"
        f"Address: {pk[:16]}...\n"
        f"\n"
        f"You can now:\n"
        f"  \u2022 Send money to anyone\n"
        f"  \u2022 Receive money from anyone\n"
        f"  \u2022 Deposit from your bank\n"
        f"  \u2022 Withdraw to your bank\n"
        f"\n"
        f"Send hi to see the menu.\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_error(msg):
    return f"Oops!\n\n{msg}\n\nReply 0 for Main Menu"


# ─── Transaction Processors ───

def process_send(phone, amount_str, to_phone):
    users = load_users()
    _, sender = find_user(users, phone)
    if not sender:
        clear_user_state(phone)
        return format_welcome()

    try:
        amount = float(amount_str.replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        clear_user_state(phone)
        return format_error("Invalid amount.")

    if not to_phone.startswith("+"):
        to_phone = "+" + to_phone

    _, receiver = find_user(users, to_phone)
    if not receiver:
        clear_user_state(phone)
        return format_error(f"{to_phone} not registered.")

    zar = get_zarc_balance(sender["public_key"])
    if zar < amount:
        clear_user_state(phone)
        return format_error(f"Insufficient.\nBalance: R{zar:,.2f}\nSending: R{amount:,.2f}")

    sender_kp = Keypair.from_secret(sender["secret_encrypted"])
    zarc = load_zarc()
    zarc_asset = Asset(zarc["asset_code"], zarc["issuer_public"])

    try:
        account = server.load_account(sender_kp.public_key)
        tx = (
            TransactionBuilder(account, NETWORK, 100)
            .add_text_memo(f"ZakaPay:R{amount:.0f} to {receiver['name']}")
            .append_payment_op(destination=receiver["public_key"], amount=f"{amount:.2f}", asset=zarc_asset)
            .set_timeout(30)
            .build()
        )
        tx.sign(sender_kp)
        resp = server.submit_transaction(tx)

        new_bal = get_zarc_balance(sender["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return format_send_success(amount, receiver["name"], to_phone, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        return format_error(f"Failed: {str(e)[:100]}")


def process_deposit(phone, amount_str):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        clear_user_state(phone)
        return format_welcome()

    try:
        amount = float(amount_str.replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        clear_user_state(phone)
        return format_error("Invalid amount.")

    if amount <= 0 or amount > 50000:
        clear_user_state(phone)
        return format_error("R1 - R50,000 only.")

    zarc = load_zarc()
    issuer_kp = Keypair.from_secret(zarc["issuer_secret"])
    zarc_asset = Asset(zarc["asset_code"], zarc["issuer_public"])

    try:
        issuer = server.load_account(issuer_kp.public_key)
        tx = (
            TransactionBuilder(issuer, NETWORK, 100)
            .add_text_memo(f"ZakaPay:Deposit:R{amount:.0f}")
            .append_payment_op(destination=user["public_key"], amount=f"{amount:.2f}", asset=zarc_asset)
            .set_timeout(30)
            .build()
        )
        tx.sign(issuer_kp)
        resp = server.submit_transaction(tx)

        new_bal = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return format_deposit_success(amount, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        return format_error(f"Failed: {str(e)[:100]}")


def process_withdraw(phone, amount_str):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        clear_user_state(phone)
        return format_welcome()

    try:
        amount = float(amount_str.replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        clear_user_state(phone)
        return format_error("Invalid amount.")

    zar = get_zarc_balance(user["public_key"])
    if zar < amount:
        clear_user_state(phone)
        return format_error(f"Insufficient.\nBalance: R{zar:,.2f}")

    zarc = load_zarc()
    user_kp = Keypair.from_secret(user["secret_encrypted"])
    zarc_asset = Asset(zarc["asset_code"], zarc["issuer_public"])

    try:
        account = server.load_account(user_kp.public_key)
        tx = (
            TransactionBuilder(account, NETWORK, 100)
            .add_text_memo(f"ZakaPay:Withdraw:R{amount:.0f}")
            .append_payment_op(destination=zarc["distribution_public"], amount=f"{amount:.2f}", asset=zarc_asset)
            .set_timeout(30)
            .build()
        )
        tx.sign(user_kp)
        resp = server.submit_transaction(tx)

        new_bal = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return format_withdraw_success(amount, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        return format_error(f"Failed: {str(e)[:100]}")


# ─── Main Message Router ───

def handle_message(message, phone):
    msg = message.strip()
    lower = msg.lower()
    parts = msg.split()

    # 0 / menu / back — always clear state and show menu
    if lower in ["0", "menu", "back"]:
        clear_user_state(phone)
        users = load_users()
        _, user = find_user(users, phone)
        return format_menu(user["name"]) if user else format_welcome()

    # Check persistent state
    state = get_user_state(phone)

    # ─── State: awaiting send ───
    if state == "awaiting_send":
        send_parts = msg.replace(",", "").split()
        if send_parts[0].lower() == "send":
            send_parts = send_parts[1:]
        if len(send_parts) >= 2:
            return process_send(phone, send_parts[0], send_parts[1])
        return format_error("Enter amount and phone.\nExample: 100 +27820000002")

    # ─── State: awaiting deposit ───
    if state == "awaiting_deposit":
        amount = lower.replace("r", "").replace(",", "").replace("deposit", "").strip()
        if amount:
            return process_deposit(phone, amount)
        return format_error("Enter the amount.\nExample: 500")

    # ─── State: awaiting withdraw ───
    if state == "awaiting_withdraw":
        amount = lower.replace("r", "").replace(",", "").replace("withdraw", "").strip()
        if amount:
            return process_withdraw(phone, amount)
        return format_error("Enter the amount.\nExample: 500")

    # ─── No state — process commands ───

    if lower in ["hi", "hello", "hey", "start", "hola"]:
        users = load_users()
        _, user = find_user(users, phone)
        return format_menu(user["name"]) if user else format_welcome()

    if lower == "1":
        users = load_users()
        _, user = find_user(users, phone)
        if not user:
            return format_welcome()
        xlm = get_balance(user["public_key"])
        zar = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = zar
        save_users(users)
        return format_balance(user["name"], zar, xlm)

    if lower == "2":
        set_user_state(phone, "awaiting_send")
        return format_send_prompt()

    if lower == "3":
        set_user_state(phone, "awaiting_deposit")
        return format_deposit_prompt()

    if lower == "4":
        set_user_state(phone, "awaiting_withdraw")
        return format_withdraw_prompt()

    if lower == "5":
        users = load_users()
        _, user = find_user(users, phone)
        if not user:
            return format_welcome()
        return (
            f"Transaction History\n\n"
            f"View on Stellar:\n"
            f"https://stellar.expert/explorer/testnet/account/{user['public_key']}\n\n"
            f"Reply 0 for Main Menu"
        )

    if lower in ["6", "help"]:
        return format_help()

    if lower.startswith("register"):
        if len(parts) < 3:
            return format_error("Usage: register YourName 1234")
        name = parts[1].title()
        pin = parts[2]
        if len(pin) < 4 or not pin.isdigit():
            return format_error("PIN must be 4+ digits.")
        users = load_users()
        _, existing = find_user(users, phone)
        if existing:
            return format_error(f"Already registered as {existing['name']}.")
        kp = Keypair.random()
        try:
            requests.get("https://friendbot.stellar.org", params={"addr": kp.public_key}, timeout=10)
        except:
            pass
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        users[phone] = {
            "name": name, "public_key": kp.public_key,
            "secret_encrypted": kp.secret, "pin_hash": pin_hash,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "zar_balance": 0
        }
        save_users(users)
        zarc = load_zarc()
        if zarc:
            try:
                za = Asset(zarc["asset_code"], zarc["issuer_public"])
                acc = server.load_account(kp.public_key)
                tx = TransactionBuilder(acc, NETWORK, 100).append_change_trust_op(asset=za, limit="100000").set_timeout(30).build()
                tx.sign(kp)
                server.submit_transaction(tx)
                ikp = Keypair.from_secret(zarc["issuer_secret"])
                ia = server.load_account(ikp.public_key)
                tx = TransactionBuilder(ia, NETWORK, 100).add_text_memo("ZakaPay:Welcome").append_payment_op(destination=kp.public_key, amount="100.00", asset=za).set_timeout(30).build()
                tx.sign(ikp)
                server.submit_transaction(tx)
                users[phone]["zar_balance"] = 100
                save_users(users)
            except:
                pass
        return format_registered(name, kp.public_key)

    if lower.startswith("send"):
        sp = msg.replace(",", "").split()
        if len(sp) >= 3:
            return process_send(phone, sp[1], sp[2])
        set_user_state(phone, "awaiting_send")
        return format_send_prompt()

    if lower.startswith("deposit"):
        amt = lower.replace("r", "").replace(",", "").replace("deposit", "").strip()
        if amt:
            return process_deposit(phone, amt)
        set_user_state(phone, "awaiting_deposit")
        return format_deposit_prompt()

    if lower.startswith("withdraw"):
        amt = lower.replace("r", "").replace(",", "").replace("withdraw", "").strip()
        if amt:
            return process_withdraw(phone, amt)
        set_user_state(phone, "awaiting_withdraw")
        return format_withdraw_prompt()

    if lower in ["balance", "bal", "zar", "rands", "money"]:
        users = load_users()
        _, user = find_user(users, phone)
        if not user:
            return format_welcome()
        xlm = get_balance(user["public_key"])
        zar = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = zar
        save_users(users)
        return format_balance(user["name"], zar, xlm)

    return f"I didn't understand that.\n\nSend hi for the menu.\nSend help for commands."


# ─── Webhooks ───

@app.route("/webhook", methods=["POST"])
def webhook_twilio():
    msg = request.form.get("Body", "").strip()
    phone = request.form.get("From", "").replace("whatsapp:", "")
    response = handle_message(msg, phone)
    from twilio.twiml.messaging_response import MessagingResponse
    resp = MessagingResponse()
    resp.message(response)
    return str(resp), 200, {"Content-Type": "text/xml"}


@app.route("/api/v1/webhook/whatsapp", methods=["POST"])
def webhook_360dialog():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    try:
        msg = data["messages"][0]["text"]["body"]
        phone = data["messages"][0]["from"]
    except:
        return jsonify({"status": "ignored"}), 200
    return jsonify({"reply": handle_message(msg, phone)}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ZakaPay API", "version": "2.2"}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({"service": "ZakaPay API", "version": "2.2", "status": "running"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

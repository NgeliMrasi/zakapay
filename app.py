#!/usr/bin/env python3
"""
ZakaPay v2.2 — Professional WhatsApp UI with Persistent State
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
DB_FILE = "users.json"
ZARC_FILE = "zarc.json"
STATE_FILE = "user_states.json"
server = Server(horizon_url=HORIZON)

# Embedded ZARC config (testnet keys — no real value)
ZARC_EMBEDDED = {
    "asset_code": "ZARC",
    "issuer_public": "GB2YP3NLSRJCO2TGIX6XYD4UQA2IG6CRUSTLUJPP4KS2OCFU6DWWPRGP",
    "issuer_secret": "SBEUK5WLNNWG4HLQUKXIZVDXVP5ZGQIZS5VVUOKEIXVHAWR3MQ24CKWP",
    "distribution_public": "GCLMUIDFWHVOZJT2XNNNXVFJMSQBQ4VNVK5533DGMYR2Z2HVZ5WUOQ5A",
    "distribution_secret": "SDQBNXN5MLGLRLLGUZGKHLX5I6SZXW275ZWP4D4ZUBD42DQ4QXR7EG6L",
    "liquidity_pool_id": "2d17f18cdf3dd9ae2eb3d226bae267d5b6095dcfe65232a7bd911541a4185f5c"
}


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
    return load_state().get(phone)


def set_user_state(phone, state):
    states = load_state()
    states[phone] = state
    save_state(states)


def clear_user_state(phone):
    states = load_state()
    states.pop(phone, None)
    save_state(states)


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
        return ZARC_EMBEDDED


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


def format_menu(name):
    return (
        f"Hello {name}! Welcome to ZakaPay.\n"
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
        f"Your Balances\n\n"
        f"Rands: R{zar:,.2f}\n"
        f"XLM: {xlm:,.2f}\n\n"
        f"1 ZARC = R1.00\n\n"
        f"Reply 0 for Main Menu"
    )


def format_send_prompt():
    return (
        f"Send Money\n\n"
        f"Enter amount and phone number:\n\n"
        f"Example:\n  100 +27820000002\n\n"
        f"Reply 0 for Main Menu"
    )


def format_send_success(amt, name, phone, bal, tx):
    return (
        f"Sent!\n\n"
        f"Amount: R{amt:,.2f}\n"
        f"To: {name}\n"
        f"Phone: {phone}\n"
        f"Your Balance: R{bal:,.2f}\n"
        f"Tx: {tx[:16]}...\n\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Reply 0 for Main Menu"
    )


def format_deposit_prompt():
    return (
        f"Deposit (Bank \u2192 ZakaPay)\n\n"
        f"Enter the amount:\n\n"
        f"Example:\n  500\n\n"
        f"Maximum: R50,000\n\n"
        f"Reply 0 for Main Menu"
    )


def format_deposit_success(amt, bal, tx):
    return (
        f"Deposit Successful!\n\n"
        f"Amount: R{amt:,.2f}\n"
        f"New Balance: R{bal:,.2f}\n"
        f"Tx: {tx[:16]}...\n\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Reply 0 for Main Menu"
    )


def format_withdraw_prompt():
    return (
        f"Withdraw (ZakaPay \u2192 Bank)\n\n"
        f"Enter the amount:\n\n"
        f"Example:\n  500\n\n"
        f"Funds arrive in 1-2 business days.\n\n"
        f"Reply 0 for Main Menu"
    )


def format_withdraw_success(amt, bal, tx):
    return (
        f"Withdrawal Successful!\n\n"
        f"Amount: R{amt:,.2f}\n"
        f"New Balance: R{bal:,.2f}\n"
        f"Tx: {tx[:16]}...\n\n"
        f"Funds in bank account in 1-2 days.\n\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Reply 0 for Main Menu"
    )


def format_help():
    return (
        f"ZakaPay Help\n\n"
        f"Menu:\n"
        f"  hi / 0  \u2014 Main menu\n"
        f"  1       \u2014 Balance\n"
        f"  2       \u2014 Send\n"
        f"  3       \u2014 Deposit\n"
        f"  4       \u2014 Withdraw\n"
        f"  5       \u2014 History\n"
        f"  6       \u2014 Help\n\n"
        f"Quick:\n"
        f"  send 100 +27xxx\n"
        f"  deposit 500\n"
        f"  register Name 1234\n\n"
        f"Support: ngeli@zakapay.africa\n"
        f"Website: zakapay.africa\n\n"
        f"Reply 0 for Main Menu"
    )


def format_welcome():
    return (
        f"Welcome to ZakaPay!\n"
        f"Banking without a bank.\n\n"
        f"You don't have a wallet yet.\n"
        f"Create one in 10 seconds:\n\n"
        f"Send: register YourName 1234\n\n"
        f"Example:\n  register Thabo 1234"
    )


def format_registered(name, pk):
    return (
        f"Welcome to ZakaPay, {name}!\n\n"
        f"Your wallet is ready.\n"
        f"Address: {pk[:16]}...\n\n"
        f"You can now:\n"
        f"  \u2022 Send money\n"
        f"  \u2022 Receive money\n"
        f"  \u2022 Deposit from bank\n"
        f"  \u2022 Withdraw to bank\n\n"
        f"Send hi to see the menu.\n\n"
        f"Reply 0 for Main Menu"
    )


def format_error(msg):
    return f"Oops!\n\n{msg}\n\nReply 0 for Main Menu"


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
    za = Asset(zarc["asset_code"], zarc["issuer_public"])
    try:
        acc = server.load_account(sender_kp.public_key)
        tx = (
            TransactionBuilder(acc, NETWORK, 100)
            .add_text_memo(f"ZakaPay:R{amount:.0f} to {receiver['name']}")
            .append_payment_op(destination=receiver["public_key"], amount=f"{amount:.2f}", asset=za)
            .set_timeout(30).build()
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
    ikp = Keypair.from_secret(zarc["issuer_secret"])
    za = Asset(zarc["asset_code"], zarc["issuer_public"])
    try:
        ia = server.load_account(ikp.public_key)
        tx = (
            TransactionBuilder(ia, NETWORK, 100)
            .add_text_memo(f"ZakaPay:Deposit:R{amount:.0f}")
            .append_payment_op(destination=user["public_key"], amount=f"{amount:.2f}", asset=za)
            .set_timeout(30).build()
        )
        tx.sign(ikp)
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
    ukp = Keypair.from_secret(user["secret_encrypted"])
    za = Asset(zarc["asset_code"], zarc["issuer_public"])
    try:
        acc = server.load_account(ukp.public_key)
        tx = (
            TransactionBuilder(acc, NETWORK, 100)
            .add_text_memo(f"ZakaPay:Withdraw:R{amount:.0f}")
            .append_payment_op(destination=zarc["distribution_public"], amount=f"{amount:.2f}", asset=za)
            .set_timeout(30).build()
        )
        tx.sign(ukp)
        resp = server.submit_transaction(tx)
        new_bal = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return format_withdraw_success(amount, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        return format_error(f"Failed: {str(e)[:100]}")


def handle_message(message, phone):
    msg = message.strip()
    lower = msg.lower()
    parts = msg.split()

    if lower in ["0", "menu", "back"]:
        clear_user_state(phone)
        users = load_users()
        _, user = find_user(users, phone)
        return format_menu(user["name"]) if user else format_welcome()

    state = get_user_state(phone)

    if state == "awaiting_send":
        sp = msg.replace(",", "").split()
        if sp[0].lower() == "send":
            sp = sp[1:]
        if len(sp) >= 2:
            return process_send(phone, sp[0], sp[1])
        return format_error("Enter amount and phone.\nExample: 100 +27820000002")

    if state == "awaiting_deposit":
        amt = lower.replace("r", "").replace(",", "").replace("deposit", "").strip()
        if amt:
            return process_deposit(phone, amt)
        return format_error("Enter the amount.\nExample: 500")

    if state == "awaiting_withdraw":
        amt = lower.replace("r", "").replace(",", "").replace("withdraw", "").strip()
        if amt:
            return process_withdraw(phone, amt)
        return format_error("Enter the amount.\nExample: 500")

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
        return f"Transaction History\n\nView on Stellar:\nhttps://stellar.expert/explorer/testnet/account/{user['public_key']}\n\nReply 0 for Main Menu"

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
        except Exception as e:
            print(f"ZARC error: {e}")
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

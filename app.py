#!/usr/bin/env python3
"""
ZakaPay v2.1 — Professional WhatsApp UI with State Tracking
Users select a menu option, then just type the amount.
No need to repeat the command word.
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
server = Server(horizon_url=HORIZON)

# ─── User State Tracking ───
# Tracks what the user is currently doing
# States: None, "awaiting_send_amount", "awaiting_deposit_amount", "awaiting_withdraw_amount"
user_states = {}


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


# ─── WhatsApp Message Formatting ───

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
        f"Or reply 0 for Main Menu"
    )


def format_send_success(amount, recipient_name, recipient_phone, new_balance, tx_hash):
    return (
        f"Sent!\n"
        f"\n"
        f"Amount: R{amount:,.2f}\n"
        f"To: {recipient_name}\n"
        f"Phone: {recipient_phone}\n"
        f"Fee: R2.50\n"
        f"Your Balance: R{new_balance:,.2f}\n"
        f"Tx: {tx_hash[:16]}...\n"
        f"\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx_hash}\n"
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


def format_deposit_success(amount, new_balance, tx_hash):
    return (
        f"Deposit Successful!\n"
        f"\n"
        f"Amount: R{amount:,.2f}\n"
        f"New Balance: R{new_balance:,.2f}\n"
        f"Tx: {tx_hash[:16]}...\n"
        f"\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx_hash}\n"
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


def format_withdraw_success(amount, new_balance, tx_hash):
    return (
        f"Withdrawal Successful!\n"
        f"\n"
        f"Amount: R{amount:,.2f}\n"
        f"New Balance: R{new_balance:,.2f}\n"
        f"Tx: {tx_hash[:16]}...\n"
        f"\n"
        f"Funds in bank account in 1-2 days.\n"
        f"\n"
        f"View: https://stellar.expert/explorer/testnet/tx/{tx_hash}\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_help():
    return (
        f"ZakaPay Help\n"
        f"\n"
        f"Menu Commands:\n"
        f"  hi / menu     \u2014 Main menu\n"
        f"  1             \u2014 Check balance\n"
        f"  2             \u2014 Send money\n"
        f"  3             \u2014 Deposit from bank\n"
        f"  4             \u2014 Withdraw to bank\n"
        f"  5             \u2014 Transaction history\n"
        f"  6             \u2014 This help page\n"
        f"\n"
        f"Quick Commands:\n"
        f"  balance       \u2014 Quick balance\n"
        f"  send 100 +27xxx \u2014 Quick send\n"
        f"  deposit 500   \u2014 Quick deposit\n"
        f"  withdraw 500  \u2014 Quick withdraw\n"
        f"  register Name 1234 \u2014 Create wallet\n"
        f"\n"
        f"Support: ngeli@zakapay.africa\n"
        f"Website: zakapay.africa\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


def format_welcome_unregistered():
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
        f"  register Thabo 1234\n"
        f"\n"
        f"Your PIN (1234) protects your wallet."
    )


def format_registration_success(name, public_key):
    return (
        f"Welcome to ZakaPay, {name}!\n"
        f"\n"
        f"Your wallet is ready.\n"
        f"Address: {public_key[:16]}...\n"
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


def format_error(error_msg):
    return (
        f"Oops!\n"
        f"\n"
        f"{error_msg}\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


# ─── Command Handlers ───

def handle_register(parts, phone):
    if len(parts) < 3:
        return format_error("Usage: register YourName 1234")

    name = parts[1].title()
    pin = parts[2]

    if len(pin) < 4 or not pin.isdigit():
        return format_error("PIN must be at least 4 digits.")

    users = load_users()
    _, existing = find_user(users, phone)
    if existing:
        return format_error(f"You already have a wallet, {existing['name']}.\n\nSend hi for the menu.")

    kp = Keypair.random()

    try:
        requests.get("https://friendbot.stellar.org", params={"addr": kp.public_key}, timeout=10)
    except:
        pass

    pin_hash = hashlib.sha256(pin.encode()).hexdigest()

    users[phone] = {
        "name": name,
        "public_key": kp.public_key,
        "secret_encrypted": kp.secret,
        "pin_hash": pin_hash,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "zar_balance": 0
    }
    save_users(users)

    zarc = load_zarc()
    if zarc:
        try:
            zarc_asset = Asset(zarc["asset_code"], zarc["issuer_public"])
            account = server.load_account(kp.public_key)
            tx = (
                TransactionBuilder(account, NETWORK, 100)
                .append_change_trust_op(asset=zarc_asset, limit="100000")
                .set_timeout(30)
                .build()
            )
            tx.sign(kp)
            server.submit_transaction(tx)

            issuer_kp = Keypair.from_secret(zarc["issuer_secret"])
            issuer_account = server.load_account(issuer_kp.public_key)
            tx = (
                TransactionBuilder(issuer_account, NETWORK, 100)
                .add_text_memo("ZakaPay:WelcomeBonus")
                .append_payment_op(
                    destination=kp.public_key,
                    amount="100.00",
                    asset=zarc_asset
                )
                .set_timeout(30)
                .build()
            )
            tx.sign(issuer_kp)
            server.submit_transaction(tx)
            users[phone]["zar_balance"] = 100
            save_users(users)
        except Exception as e:
            print(f"ZARC setup error: {e}")

    return format_registration_success(name, kp.public_key)


def handle_balance(phone):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        return format_welcome_unregistered()

    xlm = get_balance(user["public_key"])
    zar = get_zarc_balance(user["public_key"])

    users[phone]["zar_balance"] = zar
    save_users(users)

    return format_balance(user["name"], zar, xlm)


def process_send(phone, amount_str, to_phone):
    """Process a send transaction."""
    users = load_users()
    _, sender = find_user(users, phone)
    if not sender:
        user_states.pop(phone, None)
        return format_welcome_unregistered()

    try:
        amount = float(amount_str.replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        user_states.pop(phone, None)
        return format_error("Invalid amount.")

    if not to_phone.startswith("+"):
        to_phone = "+" + to_phone

    _, receiver = find_user(users, to_phone)
    if not receiver:
        user_states.pop(phone, None)
        return format_error(f"{to_phone} is not registered.\n\nThey need to register first.")

    zar_balance = get_zarc_balance(sender["public_key"])
    if zar_balance < amount:
        user_states.pop(phone, None)
        return format_error(f"Insufficient balance.\n\nBalance: R{zar_balance:,.2f}\nSending: R{amount:,.2f}")

    sender_kp = Keypair.from_secret(sender["secret_encrypted"])
    zarc = load_zarc()
    zarc_asset = Asset(zarc["asset_code"], zarc["issuer_public"])

    try:
        sender_account = server.load_account(sender_kp.public_key)
        tx = (
            TransactionBuilder(sender_account, NETWORK, 100)
            .add_text_memo(f"ZakaPay:R{amount:.0f} to {receiver['name']}")
            .append_payment_op(
                destination=receiver["public_key"],
                amount=f"{amount:.2f}",
                asset=zarc_asset
            )
            .set_timeout(30)
            .build()
        )
        tx.sign(sender_kp)
        resp = server.submit_transaction(tx)

        new_balance = get_zarc_balance(sender["public_key"])
        users[phone]["zar_balance"] = new_balance
        save_users(users)

        user_states.pop(phone, None)
        return format_send_success(amount, receiver["name"], to_phone, new_balance, resp["hash"])
    except Exception as e:
        user_states.pop(phone, None)
        return format_error(f"Transfer failed.\n\n{str(e)[:100]}")


def process_deposit(phone, amount_str):
    """Process a deposit transaction."""
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        user_states.pop(phone, None)
        return format_welcome_unregistered()

    try:
        amount = float(amount_str.replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        user_states.pop(phone, None)
        return format_error("Invalid amount.")

    if amount <= 0 or amount > 50000:
        user_states.pop(phone, None)
        return format_error("Amount must be between R1 and R50,000.")

    zarc = load_zarc()
    issuer_kp = Keypair.from_secret(zarc["issuer_secret"])
    zarc_asset = Asset(zarc["asset_code"], zarc["issuer_public"])

    try:
        issuer_account = server.load_account(issuer_kp.public_key)
        tx = (
            TransactionBuilder(issuer_account, NETWORK, 100)
            .add_text_memo(f"ZakaPay:Deposit:R{amount:.0f}")
            .append_payment_op(
                destination=user["public_key"],
                amount=f"{amount:.2f}",
                asset=zarc_asset
            )
            .set_timeout(30)
            .build()
        )
        tx.sign(issuer_kp)
        resp = server.submit_transaction(tx)

        new_balance = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_balance
        save_users(users)

        user_states.pop(phone, None)
        return format_deposit_success(amount, new_balance, resp["hash"])
    except Exception as e:
        user_states.pop(phone, None)
        return format_error(f"Deposit failed.\n\n{str(e)[:100]}")


def process_withdraw(phone, amount_str):
    """Process a withdraw transaction."""
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        user_states.pop(phone, None)
        return format_welcome_unregistered()

    try:
        amount = float(amount_str.replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        user_states.pop(phone, None)
        return format_error("Invalid amount.")

    zar_balance = get_zarc_balance(user["public_key"])
    if zar_balance < amount:
        user_states.pop(phone, None)
        return format_error(f"Insufficient balance.\n\nBalance: R{zar_balance:,.2f}\nWithdrawing: R{amount:,.2f}")

    zarc = load_zarc()
    user_kp = Keypair.from_secret(user["secret_encrypted"])
    zarc_asset = Asset(zarc["asset_code"], zarc["issuer_public"])

    try:
        user_account = server.load_account(user_kp.public_key)
        tx = (
            TransactionBuilder(user_account, NETWORK, 100)
            .add_text_memo(f"ZakaPay:Withdraw:R{amount:.0f}")
            .append_payment_op(
                destination=zarc["distribution_public"],
                amount=f"{amount:.2f}",
                asset=zarc_asset
            )
            .set_timeout(30)
            .build()
        )
        tx.sign(user_kp)
        resp = server.submit_transaction(tx)

        new_balance = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_balance
        save_users(users)

        user_states.pop(phone, None)
        return format_withdraw_success(amount, new_balance, resp["hash"])
    except Exception as e:
        user_states.pop(phone, None)
        return format_error(f"Withdrawal failed.\n\n{str(e)[:100]}")


def handle_history(phone):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        return format_welcome_unregistered()

    return (
        f"Transaction History\n"
        f"\n"
        f"View all transactions on Stellar:\n"
        f"\n"
        f"https://stellar.expert/explorer/testnet/account/{user['public_key']}\n"
        f"\n"
        f"Reply 0 for Main Menu"
    )


# ─── Main Message Router ───

def handle_message(message, phone):
    msg = message.strip()
    lower = msg.lower()
    parts = msg.split()

    # ─── Check if user is in a state (awaiting input) ───
    state = user_states.get(phone)

    # 0 always goes to main menu and clears state
    if lower in ["0", "menu", "back"]:
        user_states.pop(phone, None)
        users = load_users()
        _, user = find_user(users, phone)
        if user:
            return format_menu(user["name"])
        return format_welcome_unregistered()

    # If user is awaiting a send amount+phone
    if state == "awaiting_send":
        # Expecting: "100 +27820000002" or "send 100 +27820000002"
        send_parts = msg.replace(",", "").split()

        # If they typed "send 100 +27xxx"
        if send_parts[0].lower() == "send":
            send_parts = send_parts[1:]

        if len(send_parts) >= 2:
            amount_str = send_parts[0].replace("r", "").replace("R", "")
            to_phone = send_parts[1]
            return process_send(phone, amount_str, to_phone)
        else:
            return format_error("Please enter amount and phone number.\n\nExample: 100 +27820000002")

    # If user is awaiting a deposit amount
    if state == "awaiting_deposit":
        amount_str = lower.replace("r", "").replace("R", "").replace(",", "").replace("deposit", "").strip()
        if amount_str:
            return process_deposit(phone, amount_str)
        return format_error("Please enter the amount.\n\nExample: 500")

    # If user is awaiting a withdraw amount
    if state == "awaiting_withdraw":
        amount_str = lower.replace("r", "").replace("R", "").replace(",", "").replace("withdraw", "").strip()
        if amount_str:
            return process_withdraw(phone, amount_str)
        return format_error("Please enter the amount.\n\nExample: 500")

    # ─── No active state — process commands ───

    # Main menu / greeting
    if lower in ["hi", "hello", "hey", "start", "hola"]:
        users = load_users()
        _, user = find_user(users, phone)
        if user:
            return format_menu(user["name"])
        return format_welcome_unregistered()

    # Number shortcuts from menu
    if lower == "1":
        return handle_balance(phone)

    if lower == "2":
        user_states[phone] = "awaiting_send"
        return format_send_prompt()

    if lower == "3":
        user_states[phone] = "awaiting_deposit"
        return format_deposit_prompt()

    if lower == "4":
        user_states[phone] = "awaiting_withdraw"
        return format_withdraw_prompt()

    if lower == "5":
        return handle_history(phone)

    if lower in ["6", "help"]:
        return format_help()

    # Register
    if lower.startswith("register"):
        return handle_register(parts, phone)

    # Quick commands (bypass state)
    if lower.startswith("send"):
        send_parts = msg.replace(",", "").split()
        if len(send_parts) >= 3:
            amount_str = send_parts[1].replace("r", "").replace("R", "")
            to_phone = send_parts[2]
            return process_send(phone, amount_str, to_phone)
        user_states[phone] = "awaiting_send"
        return format_send_prompt()

    if lower.startswith("deposit"):
        amount_str = lower.replace("r", "").replace(",", "").replace("deposit", "").strip()
        if amount_str:
            return process_deposit(phone, amount_str)
        user_states[phone] = "awaiting_deposit"
        return format_deposit_prompt()

    if lower.startswith("withdraw"):
        amount_str = lower.replace("r", "").replace(",", "").replace("withdraw", "").strip()
        if amount_str:
            return process_withdraw(phone, amount_str)
        user_states[phone] = "awaiting_withdraw"
        return format_withdraw_prompt()

    if lower in ["balance", "bal", "zar", "rands", "money"]:
        return handle_balance(phone)

    # Fallback
    return (
        f"I didn't understand that.\n"
        f"\n"
        f"Send hi for the main menu.\n"
        f"Send help for all commands."
    )


# ─── Webhook Endpoints ───

@app.route("/webhook", methods=["POST"])
def webhook_twilio():
    msg = request.form.get("Body", "").strip()
    phone = request.form.get("From", "").replace("whatsapp:", "")

    response_text = handle_message(msg, phone)

    from twilio.twiml.messaging_response import MessagingResponse
    resp = MessagingResponse()
    resp.message(response_text)
    return str(resp), 200, {"Content-Type": "text/xml"}


@app.route("/api/v1/webhook/whatsapp", methods=["POST"])
def webhook_360dialog():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400

    try:
        msg = data["messages"][0]["text"]["body"]
        phone = data["messages"][0]["from"]
    except (KeyError, IndexError):
        return jsonify({"status": "ignored"}), 200

    response_text = handle_message(msg, phone)
    return jsonify({"reply": response_text}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ZakaPay API", "version": "2.1"}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "ZakaPay API",
        "version": "2.1",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "twilio_webhook": "/webhook",
            "360dialog_webhook": "/api/v1/webhook/whatsapp"
        }
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

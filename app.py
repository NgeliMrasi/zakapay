#!/usr/bin/env python3
"""
ZakaPay v3.1 — AI-Powered WhatsApp Payments
Enhanced rule-based parser + AI fallback.
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
STATE_FILE = "user_states.json"
server = Server(horizon_url=HORIZON)

ZARC_EMBEDDED = {
    "asset_code": "ZARC",
    "issuer_public": "GB2YP3NLSRJCO2TGIX6XYD4UQA2IG6CRUSTLUJPP4KS2OCFU6DWWPRGP",
    "issuer_secret": "SBEUK5WLNNWG4HLQUKXIZVDXVP5ZGQIZS5VVUOKEIXVHAWR3MQ24CKWP",
    "distribution_public": "GCLMUIDFWHVOZJT2XNNNXVFJMSQBQ4VNVK5533DGMYR2Z2HVZ5WUOQ5A",
    "distribution_secret": "SDQBNXN5MLGLRLLGUZGKHLX5I6SZXW275ZWP4D4ZUBD42DQ4QXR7EG6L",
    "liquidity_pool_id": "2d17f18cdf3dd9ae2eb3d226bae267d5b6095dcfe65232a7bd911541a4185f5c"
}


# ─── AI Intent (inline, no import issues) ───

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def ai_understand(user_message):
    """Call Groq AI for intent recognition."""
    api_key = GROQ_API_KEY
    if not api_key:
        # Try loading from .env
        try:
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY="):
                        api_key = line.split("=", 1)[1]
        except FileNotFoundError:
            pass

    if not api_key:
        print("AI: No Groq API key found")
        return None

    prompt = f"""Parse this WhatsApp message from a South African user. Return ONLY valid JSON.

Message: "{user_message}"

JSON formats:
{{"action":"send","amount":<number>,"phone":"<phone or empty>"}}
{{"action":"balance"}}
{{"action":"deposit","amount":<number>}}
{{"action":"withdraw","amount":<number>}}
{{"action":"register","name":"<name>","pin":"<pin or empty>"}}
{{"action":"help"}}
{{"action":"greeting"}}
{{"action":"history"}}
{{"action":"unknown"}}

Examples:
"yebo" → {{"action":"greeting"}}
"heita" → {{"action":"greeting"}}
"howzit" → {{"action":"greeting"}}
"show me my balance" → {{"action":"balance"}}
"check my money" → {{"action":"balance"}}
"send R100 to +27820000002" → {{"action":"send","amount":100,"phone":"+27820000002"}}
"send fifty bucks to my girl" → {{"action":"send","amount":50,"phone":""}}
"put in 500 rand" → {{"action":"deposit","amount":500}}
"take out 200" → {{"action":"withdraw","amount":200}}
"what can you do" → {{"action":"help"}}
"show my transactions" → {{"action":"history"}}

Return ONLY the JSON. Nothing else."""

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 100
            },
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()
            intent = json.loads(text)
            print(f"AI intent: {intent}")
            return intent
        else:
            print(f"AI error: {resp.status_code} - {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"AI error: {e}")
        return None


# ─── State Management ───

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


# ─── Data ───

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


# ─── Messages ───

def format_menu(name):
    return (
        f"Hello {name}! Welcome to ZakaPay.\n"
        f"Banking without a bank.\n\n"
        f"What would you like to do?\n\n"
        f"1. Check Balance\n"
        f"2. Send Money\n"
        f"3. Deposit (Bank \u2192 ZakaPay)\n"
        f"4. Withdraw (ZakaPay \u2192 Bank)\n"
        f"5. Transaction History\n"
        f"6. Help\n\n"
        f"Reply with a number (1-6)\n"
        f"Or just tell me what you need!"
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
        f"Just tell me what you need!\n\n"
        f"Examples:\n"
        f"  \"check my balance\"\n"
        f"  \"send R100 to +27820000002\"\n"
        f"  \"deposit 500\"\n"
        f"  \"withdraw 200\"\n"
        f"  \"yebo\" (greeting)\n\n"
        f"Or use the menu:\n"
        f"  1 = Balance\n"
        f"  2 = Send\n"
        f"  3 = Deposit\n"
        f"  4 = Withdraw\n"
        f"  5 = History\n"
        f"  6 = Help\n\n"
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


# ─── Transactions ───

def do_balance(phone):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        return format_welcome()
    xlm = get_balance(user["public_key"])
    zar = get_zarc_balance(user["public_key"])
    users[phone]["zar_balance"] = zar
    save_users(users)
    return format_balance(user["name"], zar, xlm)


def do_send(phone, amount_str, to_phone):
    users = load_users()
    _, sender = find_user(users, phone)
    if not sender:
        clear_user_state(phone)
        return format_welcome()
    try:
        amount = float(str(amount_str).replace("r", "").replace("R", "").replace(",", ""))
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


def do_deposit(phone, amount_str):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        clear_user_state(phone)
        return format_welcome()
    try:
        amount = float(str(amount_str).replace("r", "").replace("R", "").replace(",", ""))
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


def do_withdraw(phone, amount_str):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        clear_user_state(phone)
        return format_welcome()
    try:
        amount = float(str(amount_str).replace("r", "").replace("R", "").replace(",", ""))
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


def do_register(parts, phone):
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


def do_history(phone):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        return format_welcome()
    return f"Transaction History\n\nView on Stellar:\nhttps://stellar.expert/explorer/testnet/account/{user['public_key']}\n\nReply 0 for Main Menu"


# ─── Enhanced Rule-Based Parser ───

# South African greetings and common expressions
GREETINGS = [
    "hi", "hello", "hey", "start", "hola", "howzit",
    "yebo", "heita", "sharp", "eish", "awe", "sawubona",
    "molo", "dumela", "avuxeni", "hallo", "hi there",
    "good morning", "good afternoon", "good evening",
    "molo", "unjani", "kunjani", "hoe gaan dit"
]

BALANCE_WORDS = [
    "check my balance", "check balance",
    "balance", "bal", "zar", "rands", "money",
    "how much", "what do i have", "my money",
    "check balance", "check my balance", "show balance",
    "show me my balance", "what's my balance",
    "how much do i have", "how much money",
    "check my money", "my balance", "funds"
]

HISTORY_WORDS = [
    "history", "transactions", "tx", "statement",
    "show my transactions", "my transactions",
    "transaction history", "payment history"
]

HELP_WORDS = [
    "help", "what can you do", "commands",
    "how does this work", "how to use",
    "what do you do", "options"
]


def rule_parse(msg, phone):
    """Enhanced rule-based parser. Returns response or None."""
    lower = msg.lower().strip()
    parts = msg.split()

    # 0 / menu / back
    if lower in ["0", "menu", "back"]:
        clear_user_state(phone)
        users = load_users()
        _, user = find_user(users, phone)
        return format_menu(user["name"]) if user else format_welcome()

    # State tracking
    state = get_user_state(phone)

    if state == "awaiting_send":
        sp = msg.replace(",", "").split()
        if sp[0].lower() == "send":
            sp = sp[1:]
        if len(sp) >= 2:
            return do_send(phone, sp[0], sp[1])
        return format_error("Enter amount and phone.\nExample: 100 +27820000002")

    if state == "awaiting_deposit":
        amt = lower.replace("r", "").replace(",", "").replace("deposit", "").strip()
        if amt:
            return do_deposit(phone, amt)
        return format_error("Enter the amount.\nExample: 500")

    if state == "awaiting_withdraw":
        amt = lower.replace("r", "").replace(",", "").replace("withdraw", "").strip()
        if amt:
            return do_withdraw(phone, amt)
        return format_error("Enter the amount.\nExample: 500")

    # Greetings
    if lower in GREETINGS:
        users = load_users()
        _, user = find_user(users, phone)
        return format_menu(user["name"]) if user else format_welcome()

    # Menu numbers
    if lower == "1":
        return do_balance(phone)
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
        return do_history(phone)
    if lower in ["6", "help"]:
        return format_help()

    # Register
    if lower.startswith("register"):
        return do_register(parts, phone)

    # Quick commands
    if lower.startswith("send"):
        sp = msg.replace(",", "").split()
        if len(sp) >= 3:
            return do_send(phone, sp[1], sp[2])
        set_user_state(phone, "awaiting_send")
        return format_send_prompt()

    if lower.startswith("deposit"):
        import re
        amounts = re.findall(r'[\d]+(?:\.\d+)?', lower.replace("r", ""))
        if amounts:
            return do_deposit(phone, amounts[0])
        set_user_state(phone, "awaiting_deposit")
        return format_deposit_prompt()

    if lower.startswith("withdraw"):
        import re
        amounts = re.findall(r'[\d]+(?:\.\d+)?', lower.replace("r", ""))
        if amounts:
            return do_withdraw(phone, amounts[0])
        set_user_state(phone, "awaiting_withdraw")
        return format_withdraw_prompt()

    # Deposit intent
    if any(x in lower for x in ["deposit", "put in", "add money", "add funds", "load money", "cash in", "top up", "bank account", "from my bank", "from bank"]):
        # Check if amount is mentioned
        import re
        amounts = re.findall(r'[\d,]+(?:\.\d+)?', lower.replace("r", "").replace(",", ""))
        if amounts:
            return do_deposit(phone, amounts[0])
        set_user_state(phone, "awaiting_deposit")
        return format_deposit_prompt()

    # Withdraw intent
    if any(x in lower for x in ["withdraw", "take out", "cash out", "pull out", "get money", "send to bank"]):
        amounts = re.findall(r'[\d,]+(?:\.\d+)?', lower.replace("r", "").replace(",", ""))
        if amounts:
            return do_withdraw(phone, amounts[0])
        set_user_state(phone, "awaiting_withdraw")
        return format_withdraw_prompt()

    # Send intent (natural language)
    if any(x in lower for x in ["send money", "transfer", "pay "]):
        amounts = re.findall(r'[\d,]+(?:\.\d+)?', lower.replace("r", "").replace(",", ""))
        phones = re.findall(r'\+?\d{10,12}', msg)
        if amounts and phones:
            return do_send(phone, amounts[0], phones[0])
        elif amounts:
            set_user_state(phone, "awaiting_send")
            return f"I'll send R{amounts[0]} — who should I send it to?\n\nEnter their phone number:\nExample: +27820000002\n\nReply 0 for Main Menu"
        set_user_state(phone, "awaiting_send")
        return format_send_prompt()

    # Balance keywords
    for word in BALANCE_WORDS:
        if word in lower:
            return do_balance(phone)

    # History keywords
    for word in HISTORY_WORDS:
        if word in lower:
            return do_history(phone)

    # Help keywords
    for word in HELP_WORDS:
        if word in lower:
            return format_help()

    # Nothing matched
    return None


# ─── Main Router ───

def handle_message(message, phone):
    msg = message.strip()

    # Try rule-based parser first (fast, free)
    result = rule_parse(msg, phone)
    if result:
        return result

    # Rules didn't match — try AI
    print(f"AI fallback for: {msg}")
    intent = ai_understand(msg)
    if intent:
        action = intent.get("action", "unknown")

        if action == "greeting":
            users = load_users()
            _, user = find_user(users, phone)
            return format_menu(user["name"]) if user else format_welcome()

        if action == "balance":
            return do_balance(phone)

        if action == "send":
            amount = intent.get("amount")
            to_phone = intent.get("phone", "")
            if amount and to_phone:
                return do_send(phone, str(amount), to_phone)
            elif amount:
                set_user_state(phone, "awaiting_send")
                return f"I'll send R{amount} — who should I send it to?\n\nEnter their phone number:\nExample: +27820000002\n\nReply 0 for Main Menu"
            set_user_state(phone, "awaiting_send")
            return format_send_prompt()

        if action == "deposit":
            amount = intent.get("amount")
            if amount:
                return do_deposit(phone, str(amount))
            set_user_state(phone, "awaiting_deposit")
            return format_deposit_prompt()

        if action == "withdraw":
            amount = intent.get("amount")
            if amount:
                return do_withdraw(phone, str(amount))
            set_user_state(phone, "awaiting_withdraw")
            return format_withdraw_prompt()

        if action == "register":
            name = intent.get("name", "")
            pin = intent.get("pin", "")
            if name and pin:
                return do_register(["register", name, pin], phone)
            elif name:
                return f"Almost there! What PIN?\n\nSend: register {name} 1234"

        if action == "help":
            return format_help()

        if action == "history":
            return do_history(phone)

    # Nothing worked
    return (
        f"I didn't quite understand that.\n\n"
        f"Try:\n"
        f"  \"send R100 to +27820000002\"\n"
        f"  \"check my balance\"\n"
        f"  \"deposit 500\"\n\n"
        f"Or send hi for the menu."
    )


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
    ai_status = "connected" if GROQ_API_KEY else "no_key"
    return jsonify({"status": "ok", "service": "ZakaPay API", "version": "3.1", "ai": ai_status}), 200


@app.route("/", methods=["GET"])
def home():
    ai_status = "connected" if GROQ_API_KEY else "no_key"
    return jsonify({"service": "ZakaPay API", "version": "3.1", "status": "running", "ai": ai_status}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

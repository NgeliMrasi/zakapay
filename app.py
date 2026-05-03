#!/usr/bin/env python3
"""
ZakaPay v4.2 — AI-First + Escrow + KYC/FICA Verification
Send money to anyone. Verify identity via WhatsApp selfie + ID photo.
"""

import os
import json
import hashlib
import re
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
ESCROW_FILE = "escrow.json"
KYC_FILE = "kyc_submissions.json"
server = Server(horizon_url=HORIZON)

ZARC_EMBEDDED = {
    "asset_code": "ZARC",
    "issuer_public": "GB2YP3NLSRJCO2TGIX6XYD4UQA2IG6CRUSTLUJPP4KS2OCFU6DWWPRGP",
    "issuer_secret": "SBEUK5WLNNWG4HLQUKXIZVDXVP5ZGQIZS5VVUOKEIXVHAWR3MQ24CKWP",
    "distribution_public": "GCLMUIDFWHVOZJT2XNNNXVFJMSQBQ4VNVK5533DGMYR2Z2HVZ5WUOQ5A",
    "distribution_secret": "SDQBNXN5MLGLRLLGUZGKHLX5I6SZXW275ZWP4D4ZUBD42DQ4QXR7EG6L",
    "liquidity_pool_id": "2d17f18cdf3dd9ae2eb3d226bae267d5b6095dcfe65232a7bd911541a4185f5c"
}

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# KYC Limits
LIMITS = {
    "unverified": {"daily_send": 1000, "monthly_send": 3000, "withdraw": 500},
    "pending": {"daily_send": 1000, "monthly_send": 3000, "withdraw": 500},
    "verified": {"daily_send": 10000, "monthly_send": 50000, "withdraw": 25000},
}


def load_env():
    global GROQ_API_KEY
    if GROQ_API_KEY:
        return GROQ_API_KEY
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_API_KEY="):
                    GROQ_API_KEY = line.split("=", 1)[1]
    except FileNotFoundError:
        pass
    return GROQ_API_KEY


# ─── AI Brain ───

def ai_understand(user_message, user_name=None):
    api_key = load_env()
    if not api_key:
        return None

    context = f"The user's name is {user_name}. " if user_name else ""

    prompt = f"""You are the brain behind ZakaPay, a WhatsApp payment app in South Africa.
{context}
The user just sent this WhatsApp message. Understand what they want and return ONLY a JSON object.

Message: "{user_message}"

Possible actions:
{{"action":"greeting"}} — hi, yebo, heita, howzit, hello, hey, sawubona, dumela, what's up
{{"action":"balance"}} — check balance, how much do I have, show my money, what's my balance
{{"action":"send","amount":<number>,"phone":"<phone or empty>"}} — send money, transfer, pay someone
{{"action":"deposit","amount":<number>}} — deposit, put money in, load money, add funds, cash in, top up
{{"action":"withdraw","amount":<number>}} — withdraw, take out, cash out, pull out, get money out
{{"action":"register","name":"<name>","pin":"<pin or empty>"}} — create account, sign up, register
{{"action":"verify"}} — verify, kyc, fica, verify my account, id verification, confirm identity
{{"action":"help"}} — what can you do, help, how does this work
{{"action":"history"}} — transactions, history, statement, past payments

Rules:
- "take out 1000" → {{"action":"withdraw","amount":1000}}
- "deposit from my bank" → {{"action":"deposit","amount":0}}
- "send R500 to +27820000001" → {{"action":"send","amount":500,"phone":"+27820000001"}}
- "send money to Mamakhe" → {{"action":"send","amount":0,"phone":""}}
- "check my balance" → {{"action":"balance"}}
- "how much money do I have" → {{"action":"balance"}}
- "verify my account" → {{"action":"verify"}}
- "I want to verify" → {{"action":"verify"}}

Return ONLY the JSON. Nothing else."""

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "Return only valid JSON. No explanation."},
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
            print(f"AI: {intent}")
            return intent
        else:
            print(f"AI error: {resp.status_code}")
            return None
    except Exception as e:
        print(f"AI error: {e}")
        return None


# ─── State ───

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


# ─── Escrow ───

def load_escrow():
    try:
        with open(ESCROW_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_escrow(escrow):
    with open(ESCROW_FILE, "w") as f:
        json.dump(escrow, f, indent=2)


def add_escrow(to_phone, from_name, from_phone, amount, tx_hash):
    escrow = load_escrow()
    if to_phone not in escrow:
        escrow[to_phone] = []
    escrow[to_phone].append({
        "from_name": from_name,
        "from_phone": from_phone,
        "amount": amount,
        "tx_hash": tx_hash,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    save_escrow(escrow)


def claim_escrow(phone, user_name):
    escrow = load_escrow()
    if phone not in escrow:
        return None
    pending = escrow[phone]
    del escrow[phone]
    save_escrow(escrow)
    if not pending:
        return None
    total = sum(p["amount"] for p in pending)
    senders = [f"R{p['amount']:,.2f} from {p['from_name']}" for p in pending]
    return {"total": total, "count": len(pending), "senders": senders, "details": pending}


# ─── KYC ───

def load_kyc():
    try:
        with open(KYC_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_kyc(kyc):
    with open(KYC_FILE, "w") as f:
        json.dump(kyc, f, indent=2)


def get_kyc_status(phone):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        return None
    return user.get("kyc_status", "unverified")


def save_kyc_submission(phone, selfie_url, id_url):
    """Save KYC submission for admin review."""
    kyc = load_kyc()
    users = load_users()
    _, user = find_user(users, phone)

    kyc[phone] = {
        "name": user["name"] if user else "Unknown",
        "phone": phone,
        "selfie_url": selfie_url,
        "id_url": id_url,
        "status": "pending",
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reviewed_at": None,
        "reviewed_by": None,
        "notes": ""
    }
    save_kyc(kyc)

    # Update user status
    if user:
        users[phone]["kyc_status"] = "pending"
        save_users(users)

    return kyc[phone]


def approve_kyc(phone, reviewer="admin"):
    """Admin approves KYC."""
    kyc = load_kyc()
    users = load_users()

    if phone in kyc:
        kyc[phone]["status"] = "approved"
        kyc[phone]["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        kyc[phone]["reviewed_by"] = reviewer
        save_kyc(kyc)

    _, user = find_user(users, phone)
    if user:
        users[phone]["kyc_status"] = "verified"
        save_users(users)

    return True


def reject_kyc(phone, reason="", reviewer="admin"):
    """Admin rejects KYC."""
    kyc = load_kyc()
    users = load_users()

    if phone in kyc:
        kyc[phone]["status"] = "rejected"
        kyc[phone]["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        kyc[phone]["reviewed_by"] = reviewer
        kyc[phone]["notes"] = reason
        save_kyc(kyc)

    _, user = find_user(users, phone)
    if user:
        users[phone]["kyc_status"] = "unverified"
        save_users(users)

    return True


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


# ─── Responses ───

def resp_menu(name, kyc_status="unverified"):
    verify_option = ""
    if kyc_status == "unverified":
        verify_option = "\n7. Verify My Account"

    return (
        f"Hey {name}!\n\n"
        f"What can I do for you?\n\n"
        f"1. Check Balance\n"
        f"2. Send Money\n"
        f"3. Deposit (Bank \u2192 ZakaPay)\n"
        f"4. Withdraw (ZakaPay \u2192 Bank)\n"
        f"5. Transaction History\n"
        f"6. Help"
        f"{verify_option}\n\n"
        f"Or just tell me what you need!"
    )


def resp_balance(name, zar, xlm):
    return (
        f"{name}, here are your balances:\n\n"
        f"Rands: R{zar:,.2f}\n"
        f"XLM: {xlm:,.2f}\n\n"
        f"Anything else?"
    )


def resp_send_prompt():
    return (
        f"Sure! Who do you want to send to?\n\n"
        f"Tell me the amount and phone number:\n"
        f"Example: 100 +27820000002\n\n"
        f"Or just say the amount and I'll ask for the number."
    )


def resp_send_success(amt, name, phone, bal, tx):
    return (
        f"Sent!\n\n"
        f"R{amt:,.2f} to {name} ({phone})\n"
        f"Your balance: R{bal:,.2f}\n\n"
        f"Tx: {tx[:16]}...\n"
        f"https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Anything else?"
    )


def resp_send_escrow(amt, phone, bal, tx):
    return (
        f"Sent!\n\n"
        f"R{amt:,.2f} to {phone}\n"
        f"Your balance: R{bal:,.2f}\n\n"
        f"They haven't joined ZakaPay yet, but the money is safe.\n"
        f"When they register, they'll receive it automatically.\n\n"
        f"Tx: {tx[:16]}...\n"
        f"https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Anything else?"
    )


def resp_deposit_prompt():
    return (
        f"How much do you want to deposit?\n\n"
        f"Just tell me the amount.\n"
        f"Example: 500\n\n"
        f"Maximum: R50,000"
    )


def resp_deposit_success(amt, bal, tx):
    return (
        f"Deposit done!\n\n"
        f"R{amt:,.2f} added to your wallet.\n"
        f"New balance: R{bal:,.2f}\n\n"
        f"Tx: {tx[:16]}...\n"
        f"https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Anything else?"
    )


def resp_withdraw_prompt():
    return (
        f"How much do you want to withdraw?\n\n"
        f"Just tell me the amount.\n"
        f"Example: 500\n\n"
        f"Funds arrive in 1-2 business days."
    )


def resp_withdraw_success(amt, bal, tx):
    return (
        f"Withdrawal done!\n\n"
        f"R{amt:,.2f} sent to your bank.\n"
        f"New balance: R{bal:,.2f}\n\n"
        f"Tx: {tx[:16]}...\n"
        f"https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Funds arrive in 1-2 days. Anything else?"
    )


def resp_help():
    return (
        f"I'm ZakaPay — your WhatsApp money assistant.\n\n"
        f"Just talk to me naturally:\n\n"
        f"  \"Check my balance\"\n"
        f"  \"Send R100 to +27820000002\"\n"
        f"  \"I want to deposit 500\"\n"
        f"  \"Take out 200\"\n"
        f"  \"Show my transactions\"\n"
        f"  \"Verify my account\"\n\n"
        f"You can even send money to people who haven't registered yet.\n"
        f"They'll receive it when they join ZakaPay!\n\n"
        f"Support: ngeli@zakapay.africa"
    )


def resp_welcome():
    return (
        f"Welcome to ZakaPay!\n\n"
        f"Send and receive money through WhatsApp.\n\n"
        f"Create your wallet:\n"
        f"Send: register YourName 1234\n\n"
        f"Example: register Thabo 1234"
    )


def resp_registered(name, pk, pending=None):
    msg = (
        f"Welcome {name}! Your wallet is ready.\n\n"
        f"Address: {pk[:16]}...\n\n"
        f"You have R100.00 welcome bonus!\n\n"
        f"Here's what you can do:\n"
        f"  \u2022 Check your balance\n"
        f"  \u2022 Send money to anyone\n"
        f"  \u2022 Deposit from your bank\n"
        f"  \u2022 Withdraw to your bank\n\n"
    )

    if pending:
        msg += f"You have money waiting!\n\n"
        for sender in pending["senders"]:
            msg += f"  \u2022 {sender}\n"
        msg += f"\nTotal: R{pending['total']:,.2f}\n\n"
        msg += f"Your new balance: R{100 + pending['total']:,.2f}\n\n"

    msg += f"Just tell me what you need!"
    return msg


def resp_error(msg):
    return f"Hmm, something went wrong.\n\n{msg}\n\nTry again or send hi for the menu."


def resp_history(pk):
    return (
        f"Here's your transaction history:\n\n"
        f"https://stellar.expert/explorer/testnet/account/{pk}\n\n"
        f"Anything else?"
    )


# ─── KYC Responses ───

def resp_kyc_intro(kyc_status):
    if kyc_status == "verified":
        return (
            f"Your account is already verified!\n\n"
            f"You have full access to all ZakaPay features.\n\n"
            f"Anything else?"
        )
    elif kyc_status == "pending":
        return (
            f"Your verification is being reviewed.\n\n"
            f"We'll WhatsApp you once it's done.\n"
            f"Usually takes less than 24 hours.\n\n"
            f"Anything else?"
        )
    else:
        return (
            f"To verify your account, I need two things:\n\n"
            f"1. A clear selfie of your face\n"
            f"2. A photo of your SA ID or Passport\n\n"
            f"Send your selfie first.\n"
            f"Just take a photo and send it here."
        )


def resp_kyc_selfie_received():
    return (
        f"Selfie received!\n\n"
        f"Now send a photo of your ID book or Passport.\n"
        f"Make sure the photo is clear and all details are visible."
    )


def resp_kyc_submitted():
    return (
        f"Verification submitted!\n\n"
        f"We'll review your documents within 24 hours.\n"
        f"You'll get a WhatsApp message once verified.\n\n"
        f"What you get after verification:\n"
        f"  \u2022 Higher send limits (R10,000/month)\n"
        f"  \u2022 Higher withdrawal limits\n"
        f"  \u2022 Cross-border transfers\n"
        f"  \u2022 Full account access\n\n"
        f"Need anything else?"
    )


def resp_kyc_approved():
    return (
        f"Your account is verified!\n\n"
        f"You now have full access to ZakaPay:\n"
        f"  \u2022 Send up to R10,000/day\n"
        f"  \u2022 Withdraw up to R25,000/month\n"
        f"  \u2022 Cross-border transfers\n\n"
        f"Anything else?"
    )


def resp_kyc_rejected(reason=""):
    msg = (
        f"Verification couldn't be completed.\n\n"
    )
    if reason:
        msg += f"Reason: {reason}\n\n"
    msg += (
        f"Please try again:\n"
        f"  1. Take a clear selfie\n"
        f"  2. Take a clear photo of your ID\n\n"
        f"Make sure all text on your ID is readable.\n\n"
        f"Send your selfie to try again."
    )
    return msg


# ─── Transactions ───

def do_balance(phone):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        return resp_welcome()
    xlm = get_balance(user["public_key"])
    zar = get_zarc_balance(user["public_key"])
    users[phone]["zar_balance"] = zar
    save_users(users)
    return resp_balance(user["name"], zar, xlm)


def do_send(phone, amount_str, to_phone):
    users = load_users()
    _, sender = find_user(users, phone)
    if not sender:
        clear_user_state(phone)
        return resp_welcome()

    try:
        amount = float(str(amount_str).replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        clear_user_state(phone)
        return resp_error("I couldn't read that amount.")

    if not to_phone.startswith("+"):
        to_phone = "+" + to_phone

    zar = get_zarc_balance(sender["public_key"])
    if zar < amount:
        clear_user_state(phone)
        return resp_error(f"Not enough funds.\n\nYour balance: R{zar:,.2f}\nSending: R{amount:,.2f}")

    sender_kp = Keypair.from_secret(sender["secret_encrypted"])
    zarc = load_zarc()
    za = Asset(zarc["asset_code"], zarc["issuer_public"])

    _, receiver = find_user(users, to_phone)

    if receiver:
        try:
            acc = server.load_account(sender_kp.public_key)
            tx = (
                TransactionBuilder(acc, NETWORK, 100)
                .add_text_memo(f"ZP:{amount:.0f} to {receiver['name'][:10]}")
                .append_payment_op(destination=receiver["public_key"], amount=f"{amount:.2f}", asset=za)
                .set_timeout(30).build()
            )
            tx.sign(sender_kp)
            resp = server.submit_transaction(tx)
            time.sleep(3)
            new_bal = get_zarc_balance(sender["public_key"])
            users[phone]["zar_balance"] = new_bal
            save_users(users)
            clear_user_state(phone)
            return resp_send_success(amount, receiver["name"], to_phone, new_bal, resp["hash"])
        except Exception as e:
            clear_user_state(phone)
            return resp_error(f"Transfer failed. {str(e)[:100]}")
    else:
        try:
            escrow_kp = Keypair.random()
            requests.get("https://friendbot.stellar.org", params={"addr": escrow_kp.public_key}, timeout=10)
            time.sleep(2)

            escrow_acc = server.load_account(escrow_kp.public_key)
            tx = (
                TransactionBuilder(escrow_acc, NETWORK, 100)
                .append_change_trust_op(asset=za, limit="100000")
                .set_timeout(30).build()
            )
            tx.sign(escrow_kp)
            server.submit_transaction(tx)
            time.sleep(2)

            sender_acc = server.load_account(sender_kp.public_key)
            tx = (
                TransactionBuilder(sender_acc, NETWORK, 100)
                .add_text_memo(f"ZP:Escrow:{amount:.0f}")
                .append_payment_op(destination=escrow_kp.public_key, amount=f"{amount:.2f}", asset=za)
                .set_timeout(30).build()
            )
            tx.sign(sender_kp)
            resp = server.submit_transaction(tx)

            add_escrow(to_phone, sender["name"], phone, amount, resp["hash"])

            escrow_data = load_escrow()
            for entry in escrow_data[to_phone]:
                if entry["tx_hash"] == resp["hash"]:
                    entry["escrow_secret"] = escrow_kp.secret
                    entry["escrow_public"] = escrow_kp.public_key
            save_escrow(escrow_data)

            time.sleep(3)
            new_bal = get_zarc_balance(sender["public_key"])
            users[phone]["zar_balance"] = new_bal
            save_users(users)
            clear_user_state(phone)

            return resp_send_escrow(amount, to_phone, new_bal, resp["hash"])

        except Exception as e:
            clear_user_state(phone)
            return resp_error(f"Transfer failed. {str(e)[:100]}")


def do_deposit(phone, amount_str):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        clear_user_state(phone)
        return resp_welcome()
    try:
        amount = float(str(amount_str).replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        clear_user_state(phone)
        return resp_error("I couldn't read that amount.")
    if amount <= 0 or amount > 50000:
        clear_user_state(phone)
        return resp_error("Amount must be between R1 and R50,000.")
    zarc = load_zarc()
    ikp = Keypair.from_secret(zarc["issuer_secret"])
    za = Asset(zarc["asset_code"], zarc["issuer_public"])
    try:
        ia = server.load_account(ikp.public_key)
        tx = (
            TransactionBuilder(ia, NETWORK, 100)
            .add_text_memo(f"ZP:Deposit:{amount:.0f}")
            .append_payment_op(destination=user["public_key"], amount=f"{amount:.2f}", asset=za)
            .set_timeout(30).build()
        )
        tx.sign(ikp)
        resp = server.submit_transaction(tx)
        time.sleep(3)
        new_bal = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return resp_deposit_success(amount, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        return resp_error(f"Deposit failed. {str(e)[:100]}")


def do_withdraw(phone, amount_str):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        clear_user_state(phone)
        return resp_welcome()
    try:
        amount = float(str(amount_str).replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        clear_user_state(phone)
        return resp_error("I couldn't read that amount.")
    zar = get_zarc_balance(user["public_key"])
    if zar < amount:
        clear_user_state(phone)
        return resp_error(f"Not enough funds.\n\nYour balance: R{zar:,.2f}")
    zarc = load_zarc()
    ukp = Keypair.from_secret(user["secret_encrypted"])
    za = Asset(zarc["asset_code"], zarc["issuer_public"])
    try:
        acc = server.load_account(ukp.public_key)
        tx = (
            TransactionBuilder(acc, NETWORK, 100)
            .add_text_memo(f"ZP:Withdraw:{amount:.0f}")
            .append_payment_op(destination=zarc["distribution_public"], amount=f"{amount:.2f}", asset=za)
            .set_timeout(30).build()
        )
        tx.sign(ukp)
        resp = server.submit_transaction(tx)
        time.sleep(3)
        new_bal = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return resp_withdraw_success(amount, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        return resp_error(f"Withdrawal failed. {str(e)[:100]}")


def do_register(parts, phone):
    if len(parts) < 3:
        return resp_error("Send: register YourName 1234")
    name = parts[1].title()
    pin = parts[2]
    if len(pin) < 4 or not pin.isdigit():
        return resp_error("PIN must be at least 4 digits.")
    users = load_users()
    _, existing = find_user(users, phone)
    if existing:
        return resp_error(f"You already have a wallet, {existing['name']}.")
    kp = Keypair.random()
    try:
        requests.get("https://friendbot.stellar.org", params={"addr": kp.public_key}, timeout=10)
    except:
        pass
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    users[phone] = {
        "name": name, "public_key": kp.public_key,
        "secret_encrypted": kp.secret, "pin_hash": pin_hash,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "zar_balance": 0,
        "kyc_status": "unverified"
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
        tx = TransactionBuilder(ia, NETWORK, 100).add_text_memo("ZP:Welcome").append_payment_op(destination=kp.public_key, amount="100.00", asset=za).set_timeout(30).build()
        tx.sign(ikp)
        server.submit_transaction(tx)
        users[phone]["zar_balance"] = 100
        save_users(users)
    except Exception as e:
        print(f"ZARC error: {e}")

    pending = claim_escrow(phone, name)
    if pending:
        zarc = load_zarc()
        za = Asset(zarc["asset_code"], zarc["issuer_public"])
        total_received = 0
        for detail in pending["details"]:
            try:
                escrow_secret = detail.get("escrow_secret")
                if escrow_secret:
                    escrow_kp = Keypair.from_secret(escrow_secret)
                    escrow_balance = get_zarc_balance(escrow_kp.public_key)
                    if escrow_balance > 0:
                        escrow_acc = server.load_account(escrow_kp.public_key)
                        tx = (
                            TransactionBuilder(escrow_acc, NETWORK, 100)
                            .add_text_memo("ZP:Claimed")
                            .append_payment_op(destination=kp.public_key, amount=f"{escrow_balance:.2f}", asset=za)
                            .set_timeout(30).build()
                        )
                        tx.sign(escrow_kp)
                        server.submit_transaction(tx)
                        total_received += escrow_balance
            except Exception as e:
                print(f"Escrow claim error: {e}")
        if total_received > 0:
            new_bal = get_zarc_balance(kp.public_key)
            users[phone]["zar_balance"] = new_bal
            save_users(users)
            pending["total"] = total_received

    return resp_registered(name, kp.public_key, pending)


# ─── Main Router ───

def handle_message(message, phone, media_url=None, media_type=None):
    msg = message.strip()
    lower = msg.lower()
    parts = msg.split()

    # Quick shortcuts
    if lower in ["0", "menu", "back"]:
        clear_user_state(phone)
        users = load_users()
        _, user = find_user(users, phone)
        if user:
            kyc = user.get("kyc_status", "unverified")
            return resp_menu(user["name"], kyc)
        return resp_welcome()

    if lower.startswith("register"):
        return do_register(parts, phone)

    # State tracking
    state = get_user_state(phone)

    # ─── KYC Flow ───
    if state == "awaiting_kyc_selfie":
        if media_url and media_type and "image" in media_type:
            set_user_state(phone, "awaiting_kyc_id:" + media_url)
            return resp_kyc_selfie_received()
        else:
            return f"Please send a photo (not text).\n\nTake a clear selfie and send it as an image."

    if state and state.startswith("awaiting_kyc_id:"):
        if media_url and media_type and "image" in media_type:
            selfie_url = state.split(":", 1)[1]
            id_url = media_url
            save_kyc_submission(phone, selfie_url, id_url)
            clear_user_state(phone)
            return resp_kyc_submitted()
        else:
            return f"Please send a photo of your ID or Passport.\n\nTake a clear photo and send it as an image."

    # ─── Payment Flow States ───
    if state == "awaiting_send_amount_and_phone":
        sp = msg.replace(",", "").split()
        if len(sp) >= 2:
            return do_send(phone, sp[0], sp[1])
        elif len(sp) == 1:
            set_user_state(phone, "awaiting_send_phone:" + sp[0])
            return f"R{sp[0]} — who should I send it to?\n\nEnter their phone number:\nExample: +27820000002"
        return resp_error("Enter amount and phone.\nExample: 100 +27820000002")

    if state and state.startswith("awaiting_send_phone:"):
        amount = state.split(":")[1]
        to_phone = msg.strip().replace(" ", "")
        if not to_phone.startswith("+"):
            to_phone = "+" + to_phone
        return do_send(phone, amount, to_phone)

    if state == "awaiting_deposit_amount":
        amount = lower.replace("r", "").replace(",", "").strip()
        if amount and amount.replace(".", "").isdigit():
            return do_deposit(phone, amount)
        return resp_error("Enter the amount.\nExample: 500")

    if state == "awaiting_withdraw_amount":
        amount = lower.replace("r", "").replace(",", "").strip()
        if amount and amount.replace(".", "").isdigit():
            return do_withdraw(phone, amount)
        return resp_error("Enter the amount.\nExample: 500")

    # Menu numbers
    if lower == "1":
        clear_user_state(phone)
        return do_balance(phone)
    if lower == "2":
        set_user_state(phone, "awaiting_send_amount_and_phone")
        return resp_send_prompt()
    if lower == "3":
        set_user_state(phone, "awaiting_deposit_amount")
        return resp_deposit_prompt()
    if lower == "4":
        set_user_state(phone, "awaiting_withdraw_amount")
        return resp_withdraw_prompt()
    if lower == "5":
        clear_user_state(phone)
        users = load_users()
        _, user = find_user(users, phone)
        return resp_history(user["public_key"]) if user else resp_welcome()
    if lower in ["6", "help"]:
        clear_user_state(phone)
        return resp_help()
    if lower == "7":
        users = load_users()
        _, user = find_user(users, phone)
        if not user:
            return resp_welcome()
        kyc = user.get("kyc_status", "unverified")
        if kyc == "unverified":
            set_user_state(phone, "awaiting_kyc_selfie")
        return resp_kyc_intro(kyc)

    # Quick exact matches
    if lower in ["hi", "hello", "hey", "start"]:
        clear_user_state(phone)
        users = load_users()
        _, user = find_user(users, phone)
        if user:
            kyc = user.get("kyc_status", "unverified")
            return resp_menu(user["name"], kyc)
        return resp_welcome()
    if lower in ["balance", "bal"]:
        clear_user_state(phone)
        return do_balance(phone)

    # ─── AI BRAIN ───
    users = load_users()
    _, user = find_user(users, phone)
    user_name = user["name"] if user else None

    intent = ai_understand(msg, user_name)

    if intent:
        action = intent.get("action", "unknown")

        if action == "greeting":
            clear_user_state(phone)
            if user:
                kyc = user.get("kyc_status", "unverified")
                return resp_menu(user["name"], kyc)
            return resp_welcome()

        if action == "balance":
            clear_user_state(phone)
            return do_balance(phone)

        if action == "send":
            amount = intent.get("amount", 0)
            to_phone = intent.get("phone", "")
            if amount > 0 and to_phone:
                return do_send(phone, str(amount), to_phone)
            elif amount > 0:
                set_user_state(phone, "awaiting_send_phone:" + str(amount))
                return f"R{amount} — who should I send it to?\n\nEnter their phone number:\nExample: +27820000002"
            set_user_state(phone, "awaiting_send_amount_and_phone")
            return resp_send_prompt()

        if action == "deposit":
            amount = intent.get("amount", 0)
            if amount > 0:
                return do_deposit(phone, str(amount))
            set_user_state(phone, "awaiting_deposit_amount")
            return resp_deposit_prompt()

        if action == "withdraw":
            amount = intent.get("amount", 0)
            if amount > 0:
                return do_withdraw(phone, str(amount))
            set_user_state(phone, "awaiting_withdraw_amount")
            return resp_withdraw_prompt()

        if action == "verify":
            if not user:
                return resp_welcome()
            kyc = user.get("kyc_status", "unverified")
            if kyc == "unverified":
                set_user_state(phone, "awaiting_kyc_selfie")
            return resp_kyc_intro(kyc)

        if action == "register":
            name = intent.get("name", "")
            pin = intent.get("pin", "")
            if name and pin:
                return do_register(["register", name, pin], phone)
            elif name:
                return f"Almost there! What PIN?\n\nSend: register {name} 1234"
            return resp_error("Send: register YourName 1234")

        if action == "help":
            clear_user_state(phone)
            return resp_help()

        if action == "history":
            clear_user_state(phone)
            return resp_history(user["public_key"]) if user else resp_welcome()

    # Nothing worked
    clear_user_state(phone)
    return (
        f"I'm not sure what you mean.\n\n"
        f"Just tell me what you need:\n"
        f"  \"Check my balance\"\n"
        f"  \"Send money\"\n"
        f"  \"Deposit 500\"\n"
        f"  \"Take out 200\"\n"
        f"  \"Verify my account\"\n\n"
        f"Or send hi for the menu."
    )


# ─── Webhooks ───

@app.route("/webhook", methods=["POST"])
def webhook_twilio():
    msg = request.form.get("Body", "").strip()
    phone = request.form.get("From", "").replace("whatsapp:", "")

    # Check for media (images)
    num_media = int(request.form.get("NumMedia", 0))
    media_url = None
    media_type = None
    if num_media > 0:
        media_url = request.form.get("MediaUrl0", "")
        media_type = request.form.get("MediaContentType0", "")

    response = handle_message(msg, phone, media_url, media_type)
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

        # Check for media
        media_url = None
        media_type = None
        if "image" in data["messages"][0]:
            media_url = data["messages"][0]["image"].get("url", "")
            media_type = "image/jpeg"
    except:
        return jsonify({"status": "ignored"}), 200
    return jsonify({"reply": handle_message(msg, phone, media_url, media_type)}), 200


# ─── Admin KYC Endpoints ───

@app.route("/admin/kyc", methods=["GET"])
def admin_kyc_list():
    """List all pending KYC submissions."""
    kyc = load_kyc()
    pending = {p: d for p, d in kyc.items() if d["status"] == "pending"}
    return jsonify({"pending": len(pending), "submissions": pending}), 200


@app.route("/admin/kyc/approve/<phone>", methods=["POST"])
def admin_approve(phone):
    """Approve KYC for a user."""
    approve_kyc(phone)
    return jsonify({"status": "approved", "phone": phone}), 200


@app.route("/admin/kyc/reject/<phone>", methods=["POST"])
def admin_reject(phone):
    """Reject KYC for a user."""
    reason = request.json.get("reason", "") if request.json else ""
    reject_kyc(phone, reason)
    return jsonify({"status": "rejected", "phone": phone}), 200


@app.route("/health", methods=["GET"])
def health():
    ai_status = "connected" if GROQ_API_KEY else "no_key"
    return jsonify({"status": "ok", "service": "ZakaPay API", "version": "4.2", "ai": ai_status, "features": ["escrow", "kyc"]}), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({"service": "ZakaPay API", "version": "4.2", "status": "running"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

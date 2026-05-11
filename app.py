#!/usr/bin/env python3
"""
ZakaPay v5.0 — Cross-Border Payments + KYC + Escrow
Send money anywhere in Africa. R10 flat fee. 5 seconds.
"""

import os
import json
import hashlib
import requests
import time
from flask import Flask, request, jsonify, render_template
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

# Cross-border corridors and rates (testnet demo rates)
CORRIDORS = {
    "zimbabwe": {"country": "Zimbabwe", "currency": "USD", "rate": 0.054, "symbol": "USD", "flag": "\U0001f1ff\U0001f1fc"},
    "tanzania": {"country": "Tanzania", "currency": "TZS", "rate": 290.5, "symbol": "TZS", "flag": "\U0001f1f9\U0001f1ff"},
    "mozambique": {"country": "Mozambique", "currency": "MZN", "rate": 3.38, "symbol": "MZN", "flag": "\U0001f1f2\U0001f1ff"},
    "kenya": {"country": "Kenya", "currency": "KES", "rate": 6.95, "symbol": "KES", "flag": "\U0001f1f0\U0001f1ea"},
    "nigeria": {"country": "Nigeria", "currency": "NGN", "rate": 82.5, "symbol": "NGN", "flag": "\U0001f1f3\U0001f1ec"},
    "zambia": {"country": "Zambia", "currency": "ZMW", "rate": 1.38, "symbol": "ZMW", "flag": "\U0001f1ff\U0001f1f2"},
    "malawi": {"country": "Malawi", "currency": "MWK", "rate": 88.2, "symbol": "MWK", "flag": "\U0001f1f2\U0001f1fc"},
    "ghana": {"country": "Ghana", "currency": "GHS", "rate": 0.68, "symbol": "GHS", "flag": "\U0001f1ec\U0001f1ed"},
    "somalia": {"country": "Somalia", "currency": "USD", "rate": 0.054, "symbol": "USD", "flag": "\U0001f1f8\U0001f1f4"},
    "ethiopia": {"country": "Ethiopia", "currency": "ETB", "rate": 3.12, "symbol": "ETB", "flag": "\U0001f1ea\U0001f1f9"},
}

CROSS_BORDER_FEE = 10.00  # R10 flat fee

# Phone prefix to country mapping
PHONE_PREFIXES = {
    "+263": "zimbabwe",
    "+255": "tanzania",
    "+258": "mozambique",
    "+254": "kenya",
    "+234": "nigeria",
    "+260": "zambia",
    "+265": "malawi",
    "+233": "ghana",
    "+252": "somalia",
    "+251": "ethiopia",
}

def detect_country_from_phone(phone):
    """Detect African country from phone number prefix."""
    for prefix in sorted(PHONE_PREFIXES.keys(), key=len, reverse=True):
        if phone.startswith(prefix):
            return PHONE_PREFIXES[prefix]
    return None

def is_sa_number(phone):
    """Check if phone number is South African."""
    clean = phone.replace(" ", "").replace("-", "")
    return clean.startswith("+27")


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
{{"action":"greeting"}} — hi, yebo, heita, howzit, hello, hey, sawubona, dumela
{{"action":"balance"}} — check balance, how much do I have, show my money
{{"action":"send","amount":<number>,"phone":"<phone or empty>"}} — send money, transfer, pay someone
{{"action":"deposit","amount":<number>}} — deposit, put money in, load money, cash in, top up
{{"action":"withdraw","amount":<number>}} — withdraw, take out, cash out, pull out
{{"action":"crossborder","amount":<number>,"country":"<country or empty>"}} — send money abroad, send to zimbabwe, send to tanzania, international transfer, remit, cross border, send money home, send to my family in africa
{{"action":"verify"}} — verify, kyc, fica, verify my account
{{"action":"help"}} — what can you do, help, how does this work
{{"action":"history"}} — transactions, history, statement

Rules:
- "send money to zimbabwe" → {{"action":"crossborder","amount":0,"country":"zimbabwe"}}
- "send 500 to tanzania" → {{"action":"crossborder","amount":500,"country":"tanzania"}}
- "remit 1000" → {{"action":"crossborder","amount":1000,"country":""}}
- "send money to my family in mozambique" → {{"action":"crossborder","amount":0,"country":"mozambique"}}
- "cross border transfer" → {{"action":"crossborder","amount":0,"country":""}}
- "take out 1000" → {{"action":"withdraw","amount":1000}}
- "send R500 to +27820000001" → {{"action":"send","amount":500,"phone":"+27820000001"}}
- "check my balance" → {{"action":"balance"}}

Return ONLY the JSON. Nothing else."""
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json={"model": "llama-3.1-8b-instant", "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt}
            ], "temperature": 0.1, "max_tokens": 100},
            timeout=10
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()
            return json.loads(text)
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
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(states, f, indent=2)
    except Exception as e:
        print(f"STATE SAVE ERROR: {e}")

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
    try:
        with open(DB_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"DB SAVE ERROR: {e}")

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

def stellar_safe(func, *args, **kwargs):
    """Execute a Stellar operation with retry logic."""
    for attempt in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Stellar attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise
            time.sleep(2)

def find_user(users, phone):
    clean = phone.replace(" ", "").replace("-", "")
    for p, u in users.items():
        if p == clean:
            return p, u
    return None, None


# ─── Escrow ───

def load_escrow():
    try:
        with open(ESCROW_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_escrow(escrow):
    try:
        with open(ESCROW_FILE, "w") as f:
            json.dump(escrow, f, indent=2)
    except Exception as e:
        print(f"ESCROW SAVE ERROR: {e}")

def add_escrow(to_phone, from_name, from_phone, amount, tx_hash):
    escrow = load_escrow()
    if to_phone not in escrow:
        escrow[to_phone] = []
    escrow[to_phone].append({
        "from_name": from_name, "from_phone": from_phone,
        "amount": amount, "tx_hash": tx_hash,
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
    try:
        with open(KYC_FILE, "w") as f:
            json.dump(kyc, f, indent=2)
    except Exception as e:
        print(f"KYC SAVE ERROR: {e}")

def get_kyc_by_phone(phone):
    return load_kyc().get(phone, None)

def save_kyc_submission(phone, selfie_url, id_url):
    kyc = load_kyc()
    kyc[phone] = {
        "phone": phone, "selfie_url": selfie_url, "id_url": id_url,
        "status": "pending", "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reviewed_at": None, "reviewed_by": None, "notes": ""
    }
    save_kyc(kyc)
    return kyc[phone]

def approve_kyc(phone, reviewer="admin"):
    kyc = load_kyc()
    if phone in kyc:
        kyc[phone]["status"] = "approved"
        kyc[phone]["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        kyc[phone]["reviewed_by"] = reviewer
        save_kyc(kyc)
    users = load_users()
    _, user = find_user(users, phone)
    if user:
        users[phone]["kyc_status"] = "verified"
        save_users(users)
    return True

def reject_kyc(phone, reason="", reviewer="admin"):
    kyc = load_kyc()
    if phone in kyc:
        kyc[phone]["status"] = "rejected"
        kyc[phone]["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        kyc[phone]["reviewed_by"] = reviewer
        kyc[phone]["notes"] = reason
        save_kyc(kyc)
    return True


# ─── Responses ───

def resp_menu(name, kyc_status="unverified"):
    verify_option = ""
    if kyc_status == "unverified":
        verify_option = "\n8. Verify My Account"
    return (
        f"Hey {name}!\n\n"
        f"What can I do for you?\n\n"
        f"1. Check Balance\n"
        f"2. Send Money\n"
        f"3. Deposit (Bank \u2192 ZakaPay)\n"
        f"4. Withdraw (ZakaPay \u2192 Bank)\n"
        f"5. Send Money Abroad\n"
        f"6. Transaction History\n"
        f"7. Help"
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
        f"Instant withdrawal to your bank."
    )

def resp_withdraw_success(amt, bal, tx):
    return (
        f"Withdrawal done!\n\n"
        f"R{amt:,.2f} sent to your bank.\n"
        f"New balance: R{bal:,.2f}\n\n"
        f"Tx: {tx[:16]}...\n"
        f"https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Withdrawal complete! Anything else?"
    )

def resp_help():
    return (
        f"I'm ZakaPay — your WhatsApp money assistant.\n\n"
        f"Just talk to me naturally:\n\n"
        f"  \"Check my balance\"\n"
        f"  \"Send R100 to +27820000002\"\n"
        f"  \"I want to deposit 500\"\n"
        f"  \"Take out 200\"\n"
        f"  \"Send money to Zimbabwe\"\n"
        f"  \"Send 1000 to Tanzania\"\n"
        f"  \"Show my transactions\"\n\n"
        f"Cross-border: R10 flat fee. 5 seconds. Anywhere in Africa.\n\n"
        f"Support: ngeli@zakapay.africa"
    )

def resp_history(pk):
    return (
        f"Here's your transaction history:\n\n"
        f"https://stellar.expert/explorer/testnet/account/{pk}\n\n"
        f"Anything else?"
    )

def resp_error(msg):
    return f"Hmm, something went wrong.\n\n{msg}\n\nTry again or send hi for the menu."


# ─── Cross-Border Responses ───

def resp_crossborder_prompt():
    corridors = "\n".join([f"  {v['flag']} {v['country']}" for v in CORRIDORS.values()])
    return (
        f"Send money anywhere in Africa!\n\n"
        f"R10 flat fee. Arrives in 5 seconds.\n\n"
        f"Where are you sending?\n\n"
        f"{corridors}\n\n"
        f"Just tell me the country name."
    )

def resp_crossborder_amount(country_info):
    return (
        f"Sending to {country_info['flag']} {country_info['country']}.\n\n"
        f"How much do you want to send (in Rands)?\n\n"
        f"Example: 1000\n\n"
        f"Fee: R10.00 flat\n"
        f"Rate: R1 = {country_info['rate']} {country_info['currency']}"
    )

def resp_crossborder_confirm(amount, country_info, recipient_phone=""):
    fee = CROSS_BORDER_FEE
    total = amount + fee
    converted = (amount - fee) * country_info["rate"]
    to_line = f"  To: {recipient_phone}\n" if recipient_phone else ""
    return (
        f"Confirm cross-border transfer:\n\n"
        f"  Sending: R{amount:,.2f}\n"
        f"  Fee: R{fee:,.2f}\n"
        f"  Total: R{total:,.2f}\n\n"
        f"  They receive: {country_info['symbol']} {converted:,.2f}\n"
        f"  Destination: {country_info['flag']} {country_info['country']}\n"
        f"{to_line}\n"
        f"Reply YES to confirm or NO to cancel."
    )

def resp_crossborder_success(amount, country_info, bal, tx):
    fee = CROSS_BORDER_FEE
    converted = (amount - fee) * country_info["rate"]
    return (
        f"Cross-border transfer sent!\n\n"
        f"  R{amount:,.2f} \u2192 {country_info['flag']} {country_info['country']}\n"
        f"  They receive: {country_info['symbol']} {converted:,.2f}\n"
        f"  Fee: R{fee:,.2f}\n"
        f"  Your balance: R{bal:,.2f}\n\n"
        f"  Arrives in 5 seconds.\n\n"
        f"Tx: {tx[:16]}...\n"
        f"https://stellar.expert/explorer/testnet/tx/{tx}\n\n"
        f"Anything else?"
    )


# ─── KYC Responses ───

def resp_new_user():
    return (
        f"Hey! Welcome to ZakaPay.\n\n"
        f"I help you send and receive money through WhatsApp.\n\n"
        f"Before we get started, I need to verify your identity.\n\n"
        f"Step 1: Send me a selfie.\n"
        f"Just take a clear photo of your face and send it here."
    )

def resp_kyc_selfie_received():
    return (
        f"Selfie received!\n\n"
        f"Step 2: Send me a photo of your SA ID or Passport.\n"
        f"Make sure all the details are visible and the photo is clear."
    )

def resp_kyc_submitted():
    return (
        f"Verification submitted!\n\n"
        f"We'll review your documents within 24 hours.\n"
        f"Come back and say hi to check your status.\n\n"
        f"See you soon!"
    )

def resp_kyc_pending():
    return (
        f"Welcome back!\n\n"
        f"Your verification is still being reviewed.\n"
        f"We'll WhatsApp you once it's done.\n\n"
        f"Usually takes less than 24 hours."
    )

def resp_kyc_approved():
    return (
        f"Great news \u2014 you're verified!\n\n"
        f"Now let's create your wallet.\n"
        f"What should I call you?"
    )

def resp_kyc_rejected(reason=""):
    msg = f"Verification couldn't be completed.\n\n"
    if reason:
        msg += f"Reason: {reason}\n\n"
    msg += f"Let's try again.\n\nSend me a clear selfie."
    return msg

def resp_registered(name, pk, pending=None):
    msg = (
        f"You're all set, {name}!\n\n"
        f"Your wallet is ready.\n"
        f"Address: {pk[:16]}...\n\n"
        f"You have R100.00 welcome bonus!\n\n"
    )
    if pending:
        msg += f"You also have money waiting!\n\n"
        for sender in pending["senders"]:
            msg += f"  \u2022 {sender}\n"
        msg += f"\nTotal: R{pending['total']:,.2f}\n\n"
        msg += f"Your balance: R{100 + pending['total']:,.2f}\n\n"
    msg += (
        f"What would you like to do?\n\n"
        f"  \u2022 Check your balance\n"
        f"  \u2022 Send money\n"
        f"  \u2022 Deposit from your bank\n"
        f"  \u2022 Withdraw to your bank\n"
        f"  \u2022 Send money abroad\n\n"
        f"Just tell me what you need!"
    )
    return msg


# ─── Transactions ───

def do_balance(phone):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        return None
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
        return None
    try:
        amount = float(str(amount_str).replace("r", "").replace("R", "").replace(",", ""))
    except ValueError:
        clear_user_state(phone)
        return resp_error("I couldn't read that amount.")
    if not to_phone.startswith("+"):
        to_phone = "+" + to_phone

    # Check if this is a foreign number — route to cross-border
    if not is_sa_number(to_phone):
        country = detect_country_from_phone(to_phone)
        if country and country in CORRIDORS:
            country_info = CORRIDORS[country]
            clear_user_state(phone)
            set_user_state(phone, "awaiting_xborder_confirm:" + country + ":" + str(amount) + ":" + to_phone)
            return resp_crossborder_confirm(amount, country_info, to_phone)
        else:
            clear_user_state(phone)
            return resp_error(f"International transfers to this number are not supported yet.\n\nSupported: Zimbabwe, Tanzania, Mozambique, Kenya, Nigeria, Zambia, Malawi, Ghana")
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
            time.sleep(1)
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
            for attempt in range(3):
                try:
                    escrow_acc = server.load_account(escrow_kp.public_key)
                    tx = (
                        TransactionBuilder(escrow_acc, NETWORK, 100)
                        .append_change_trust_op(asset=za, limit="100000")
                        .set_timeout(30).build()
                    )
                    tx.sign(escrow_kp)
                    server.submit_transaction(tx)
                    break
                except:
                    time.sleep(1)
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
            new_bal = get_zarc_balance(sender["public_key"])
            users[phone]["zar_balance"] = new_bal
            save_users(users)
            clear_user_state(phone)
            return resp_send_escrow(amount, to_phone, new_bal, resp["hash"])
        except Exception as e:
            clear_user_state(phone)
            return resp_error(f"Transfer failed. {str(e)[:100]}")



def do_crossborder(phone, amount, country_key, recipient_phone=""):
    """Execute cross-border transfer via Stellar DEX."""
    try:
        users = load_users()
        _, sender = find_user(users, phone)
        if not sender:
            clear_user_state(phone)
            return None
        country_info = CORRIDORS.get(country_key)
        if not country_info:
            clear_user_state(phone)
            return resp_error("Unknown country.")
        fee = CROSS_BORDER_FEE
        total = amount + fee
        zar = get_zarc_balance(sender["public_key"])
        if zar < total:
            clear_user_state(phone)
            return resp_error(f"Not enough funds.\n\nBalance: R{zar:,.2f}\nNeed: R{total:,.2f}")
        sender_kp = Keypair.from_secret(sender["secret_encrypted"])
        zarc = load_zarc()
        za = Asset(zarc["asset_code"], zarc["issuer_public"])
        acc = server.load_account(sender_kp.public_key)
        converted = (amount - fee) * country_info["rate"]
        memo = f"ZP:XB:{amount:.0f}"
        tx = (
            TransactionBuilder(acc, NETWORK, 100)
            .add_text_memo(memo)
            .append_payment_op(destination=zarc["issuer_public"], amount=f"{total:.2f}", asset=za)
            .set_timeout(30).build()
        )
        tx.sign(sender_kp)
        resp = server.submit_transaction(tx)
        time.sleep(1)
        new_bal = get_zarc_balance(sender["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return resp_crossborder_success(amount, country_info, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        error_str = str(e)
        print(f"X-BORDER ERROR: {error_str}")
        try:
            import json as _json
            if "{" in error_str:
                body = _json.loads(error_str)
                extras = body.get("extras", {}).get("result_codes", {})
                ops = extras.get("operations", ["unknown"])
                return resp_error(f"Stellar: {ops}")
        except:
            pass
        return resp_error(f"Transfer failed. {error_str[:280]}")


def do_deposit(phone, amount_str):
    users = load_users()
    _, user = find_user(users, phone)
    if not user:
        clear_user_state(phone)
        return None
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
        time.sleep(1)
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
        return None
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
            .append_payment_op(destination=zarc["issuer_public"], amount=f"{amount:.2f}", asset=za)
            .set_timeout(30).build()
        )
        tx.sign(ukp)
        resp = server.submit_transaction(tx)
        time.sleep(1)
        new_bal = get_zarc_balance(user["public_key"])
        users[phone]["zar_balance"] = new_bal
        save_users(users)
        clear_user_state(phone)
        return resp_withdraw_success(amount, new_bal, resp["hash"])
    except Exception as e:
        clear_user_state(phone)
        return resp_error(f"Withdrawal failed. {str(e)[:100]}")


def do_create_wallet(name, pin, phone):
    try:
        return _do_create_wallet_inner(name, pin, phone)
    except Exception as e:
        print(f"WALLET CRASH: {e}")
        return resp_error("Could not create wallet. Please try again.")

def _do_create_wallet_inner(name, pin, phone):
    users = load_users()
    _, existing = find_user(users, phone)
    if existing:
        return resp_error(f"You already have a wallet, {existing['name']}.")
    kp = Keypair.random()
    try:
        requests.get("https://friendbot.stellar.org", params={"addr": kp.public_key}, timeout=10)
        time.sleep(2)
    except:
        pass
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    users[phone] = {
        "name": name, "public_key": kp.public_key,
        "secret_encrypted": kp.secret, "pin_hash": pin_hash,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "zar_balance": 0,
        "kyc_status": "verified"
    }
    save_users(users)
    zarc = load_zarc()
    za = Asset(zarc["asset_code"], zarc["issuer_public"])
    try:
        acc = server.load_account(kp.public_key)
        tx = TransactionBuilder(acc, NETWORK, 100).append_change_trust_op(asset=za, limit="100000").set_timeout(30).build()
        tx.sign(kp)
        server.submit_transaction(tx)
        time.sleep(1)
        ikp = Keypair.from_secret(zarc["issuer_secret"])
        ia = server.load_account(ikp.public_key)
        tx = TransactionBuilder(ia, NETWORK, 100).add_text_memo("ZP:Welcome").append_payment_op(destination=kp.public_key, amount="100.00", asset=za).set_timeout(30).build()
        tx.sign(ikp)
        server.submit_transaction(tx)
        users[phone]["zar_balance"] = 100
        save_users(users)
    except Exception as e:
        print(f"WALLET ZARC ERROR: {e}")
    pending = None
    try:
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
    except Exception as e:
        print(f"Escrow claim crash: {e}")
        pending = None
    return resp_registered(name, kp.public_key, pending)


# ─── Main Router ───

def handle_message(message, phone, media_url=None, media_type=None):
    try:
        return _handle_message_inner(message, phone, media_url, media_type)
    except Exception as e:
        print(f"HANDLE ERROR: {e}")
        return "Something went wrong. Send hi to try again."

def _handle_message_inner(message, phone, media_url=None, media_type=None):
    msg = message.strip()
    lower = msg.lower()
    parts = msg.split()

    # Check if user exists
    users = load_users()
    _, user = find_user(users, phone)

    # ═══════════════════════════════════════
    # STEP 1: ALWAYS CHECK GREETING FIRST
    # This MUST come before state checks
    # ═══════════════════════════════════════
    if lower in ["hi", "hello", "hey", "start", "yebo", "howzit", "heita", "0", "menu", "back"]:
        clear_user_state(phone)
        if user:
            kyc = user.get("kyc_status", "unverified")
            return resp_menu(user["name"], kyc)
        kyc = get_kyc_by_phone(phone)
        if kyc and kyc["status"] == "approved":
            set_user_state(phone, "awaiting_name")
            return resp_kyc_approved()
        elif kyc and kyc["status"] == "pending":
            return resp_kyc_pending()
        elif kyc and kyc["status"] == "rejected":
            set_user_state(phone, "awaiting_kyc_selfie")
            return resp_kyc_rejected(kyc.get("notes", ""))
        else:
            set_user_state(phone, "awaiting_kyc_selfie")
            return resp_new_user()

    # ═══════════════════════════════════════
    # STEP 2: GET STATE
    # ═══════════════════════════════════════
    state = get_user_state(phone)

    # ─── KYC Flow ───
    if state == "awaiting_kyc_selfie":
        if media_url and media_type and "image" in media_type:
            set_user_state(phone, "awaiting_kyc_id:" + media_url)
            return resp_kyc_selfie_received()
        return f"Please send a photo (not text).\n\nTake a clear selfie of your face and send it as an image."

    if state and state.startswith("awaiting_kyc_id:"):
        if media_url and media_type and "image" in media_type:
            selfie_url = state.split(":", 1)[1]
            save_kyc_submission(phone, selfie_url, media_url)
            clear_user_state(phone)
            return resp_kyc_submitted()
        return f"Please send a photo of your ID or Passport.\n\nTake a clear photo and send it as an image."

    # ─── Registration Flow ───
    if state == "awaiting_name":
        name = msg.strip().title()
        if len(name) < 2 or len(name) > 30:
            return f"Please enter a valid name."
        set_user_state(phone, "awaiting_pin:" + name)
        return f"Nice to meet you, {name}!\n\nPick a 4-digit PIN to secure your account."

    if state and state.startswith("awaiting_pin:"):
        pin = msg.strip()
        name = state.split(":", 1)[1]
        if not pin.isdigit() or len(pin) < 4:
            return f"PIN must be at least 4 digits. Try again."
        clear_user_state(phone)
        return do_create_wallet(name, pin, phone)

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

    # ─── Cross-Border Flow States ───
    if state == "awaiting_xborder_country":
        # Try to detect country from phone number in the message
        detected_phone = None
        detected_country = None
        for word in msg.replace(" ", "").split():
            clean = word.strip()
            if clean.startswith("+") or clean.startswith("2"):
                if not clean.startswith("+"):
                    clean = "+" + clean
                country = detect_country_from_phone(clean)
                if country:
                    detected_phone = clean
                    detected_country = country
                    break

        if detected_country:
            country_info = CORRIDORS[detected_country]
            set_user_state(phone, "awaiting_xborder_amount:" + detected_country + ":" + (detected_phone or ""))
            return (
                f"{country_info['flag']} {country_info['country']} detected from {detected_phone}\n\n"
                f"How much do you want to send (in Rands)?\n\n"
                f"Example: 1000\n\n"
                f"Fee: R10.00 flat\n"
                f"Rate: R1 = {country_info['rate']} {country_info['currency']}"
            )

        # Try matching by country name
        for key, info in CORRIDORS.items():
            if key in lower or info["country"].lower() in lower:
                set_user_state(phone, "awaiting_xborder_amount:" + key + ":")
                return resp_crossborder_amount(info)

        return (
            f"I need a phone number to detect the country.\n\n"
            f"Example: +263771234567 (Zimbabwe)\n"
            f"Or tell me the country name: Zimbabwe, Tanzania, etc."
        )

    if state and state.startswith("awaiting_xborder_amount:"):
        parts_state = state.split(":")
        country_key = parts_state[1]
        recipient_phone = parts_state[2] if len(parts_state) > 2 else ""
        amount_str = lower.replace("r", "").replace(",", "").strip()
        if amount_str and amount_str.replace(".", "").isdigit():
            amount = float(amount_str)
            country_info = CORRIDORS.get(country_key)
            if not country_info:
                clear_user_state(phone)
                return resp_error("Country not found.")
            set_user_state(phone, "awaiting_xborder_confirm:" + country_key + ":" + str(amount) + ":" + recipient_phone)
            return resp_crossborder_confirm(amount, country_info, recipient_phone)
        return resp_error("Enter the amount in Rands.\nExample: 1000")

    if state and state.startswith("awaiting_xborder_confirm:"):
        parts_state = state.split(":")
        country_key = parts_state[1]
        amount = float(parts_state[2])
        recipient_phone = parts_state[3] if len(parts_state) > 3 else ""
        if lower in ["yes", "y", "confirm", "ok"]:
            return do_crossborder(phone, amount, country_key, recipient_phone)
        elif lower in ["no", "n", "cancel"]:
            clear_user_state(phone)
            return f"Transfer cancelled.\n\nAnything else?"
        return f"Reply YES to confirm or NO to cancel."

    # Menu numbers
    users = load_users()
    _, user = find_user(users, phone)

    if lower == "1" and user:
        clear_user_state(phone)
        return do_balance(phone)
    if lower == "2" and user:
        set_user_state(phone, "awaiting_send_amount_and_phone")
        return resp_send_prompt()
    if lower == "3" and user:
        set_user_state(phone, "awaiting_deposit_amount")
        return resp_deposit_prompt()
    if lower == "4" and user:
        set_user_state(phone, "awaiting_withdraw_amount")
        return resp_withdraw_prompt()
    if lower == "5" and user:
        set_user_state(phone, "awaiting_xborder_country")
        return resp_crossborder_prompt()
    if lower in ["6", "history"] and user:
        clear_user_state(phone)
        return resp_history(user["public_key"])
    if lower in ["7", "help"]:
        clear_user_state(phone)
        return resp_help()
    if lower == "8" and user:
        kyc = user.get("kyc_status", "unverified")
        if kyc == "unverified":
            set_user_state(phone, "awaiting_kyc_selfie")
            return f"To verify your account, send me:\n\n1. A selfie\n2. A photo of your SA ID or Passport\n\nSend your selfie first."
        elif kyc == "pending":
            return f"Your verification is being reviewed."
        else:
            return f"Your account is already verified!"

    if lower in ["balance", "bal"] and user:
        clear_user_state(phone)
        return do_balance(phone)

    # ─── AI BRAIN ───
    user_name = user["name"] if user else None
    intent = ai_understand(msg, user_name)

    if intent:
        action = intent.get("action", "unknown")

        if action == "greeting":
            clear_user_state(phone)
            if user:
                kyc = user.get("kyc_status", "unverified")
                return resp_menu(user["name"], kyc)
            kyc = get_kyc_by_phone(phone)
            if kyc and kyc["status"] == "approved":
                set_user_state(phone, "awaiting_name")
                return resp_kyc_approved()
            elif kyc and kyc["status"] == "pending":
                return resp_kyc_pending()
            elif kyc and kyc["status"] == "rejected":
                set_user_state(phone, "awaiting_kyc_selfie")
                return resp_kyc_rejected(kyc.get("notes", ""))
            else:
                set_user_state(phone, "awaiting_kyc_selfie")
                return resp_new_user()

        if action == "balance" and user:
            clear_user_state(phone)
            return do_balance(phone)

        if action == "send" and user:
            amount = intent.get("amount", 0)
            to_phone = intent.get("phone", "")
            if amount > 0 and to_phone:
                return do_send(phone, str(amount), to_phone)
            elif amount > 0:
                set_user_state(phone, "awaiting_send_phone:" + str(amount))
                return f"R{amount} — who should I send it to?\n\nEnter their phone number:\nExample: +27820000002"
            set_user_state(phone, "awaiting_send_amount_and_phone")
            return resp_send_prompt()

        if action == "deposit" and user:
            amount = intent.get("amount", 0)
            if amount > 0:
                return do_deposit(phone, str(amount))
            set_user_state(phone, "awaiting_deposit_amount")
            return resp_deposit_prompt()

        if action == "withdraw" and user:
            amount = intent.get("amount", 0)
            if amount > 0:
                return do_withdraw(phone, str(amount))
            set_user_state(phone, "awaiting_withdraw_amount")
            return resp_withdraw_prompt()

        if action == "crossborder" and user:
            amount = intent.get("amount", 0)
            country = intent.get("country", "").lower()
            # Try to detect country from phone number in original message
            detected_phone = None
            for word in msg.replace(" ", "").split():
                clean = word.strip()
                if clean.startswith("+") or (clean.startswith("2") and len(clean) > 9):
                    if not clean.startswith("+"):
                        clean = "+" + clean
                    detected = detect_country_from_phone(clean)
                    if detected:
                        country = detected
                        detected_phone = clean
                        break
            if country and country in CORRIDORS:
                if amount > 0 and detected_phone:
                    set_user_state(phone, "awaiting_xborder_confirm:" + country + ":" + str(amount) + ":" + detected_phone)
                    return resp_crossborder_confirm(amount, CORRIDORS[country], detected_phone)
                elif detected_phone:
                    set_user_state(phone, "awaiting_xborder_amount:" + country + ":" + detected_phone)
                    return resp_crossborder_amount(CORRIDORS[country])
                elif amount > 0:
                    # Have amount but no phone — ask for phone
                    set_user_state(phone, "awaiting_xborder_recipient:" + country)
                    return (
                        f"Sending to {CORRIDORS[country]['flag']} {CORRIDORS[country]['country']}.\n\n"
                        f"What\'s the recipient\'s phone number?\n"
                        f"Example: +263771234567"
                    )
            # No country detected — ask for phone number
            set_user_state(phone, "awaiting_xborder_country")
            return resp_crossborder_prompt()

        if action == "verify":
            if user:
                kyc = user.get("kyc_status", "unverified")
                if kyc == "unverified":
                    set_user_state(phone, "awaiting_kyc_selfie")
                    return f"To verify your account, send me:\n\n1. A selfie\n2. A photo of your SA ID or Passport\n\nSend your selfie first."
                elif kyc == "pending":
                    return f"Your verification is being reviewed."
                else:
                    return f"Your account is already verified!"
            else:
                kyc = get_kyc_by_phone(phone)
                if kyc and kyc["status"] == "approved":
                    set_user_state(phone, "awaiting_name")
                    return resp_kyc_approved()
                elif kyc and kyc["status"] == "pending":
                    return resp_kyc_pending()
                else:
                    set_user_state(phone, "awaiting_kyc_selfie")
                    return resp_new_user()

        if action == "help":
            clear_user_state(phone)
            return resp_help()

        if action == "history" and user:
            clear_user_state(phone)
            return resp_history(user["public_key"])

    # Nothing worked
    clear_user_state(phone)
    if user:
        return (
            f"I'm not sure what you mean.\n\n"
            f"Just tell me what you need:\n"
            f"  \"Check my balance\"\n"
            f"  \"Send money\"\n"
            f"  \"Send money to Zimbabwe\"\n"
            f"  \"Deposit 500\"\n\n"
            f"Or send hi for the menu."
        )
    else:
        set_user_state(phone, "awaiting_kyc_selfie")
        return resp_new_user()


# ─── Webhooks ───

@app.route("/webhook", methods=["POST"])
def webhook_twilio():
    try:
        msg = request.form.get("Body", "").strip()
        phone = request.form.get("From", "").replace("whatsapp:", "")
        num_media = int(request.form.get("NumMedia", 0))
        media_url = None
        media_type = None
        if num_media > 0:
            media_url = request.form.get("MediaUrl0", "")
            media_type = request.form.get("MediaContentType0", "")
        response = handle_message(msg, phone, media_url, media_type)
    except Exception as e:
        print(f"WEBHOOK ERROR: {e}")
        response = "Something went wrong. Send hi to try again."
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
        media_url = None
        media_type = None
        if "image" in data["messages"][0]:
            media_url = data["messages"][0]["image"].get("url", "")
            media_type = "image/jpeg"
    except:
        return jsonify({"status": "ignored"}), 200
    return jsonify({"reply": handle_message(msg, phone, media_url, media_type)}), 200


# ─── Admin ───

@app.route("/admin", methods=["GET"])
def admin_dashboard():
    return render_template("admin.html")

@app.route("/admin/kyc", methods=["GET"])
def admin_kyc_list():
    kyc = load_kyc()
    pending = {p: d for p, d in kyc.items() if d["status"] == "pending"}
    return jsonify({"pending": len(pending), "submissions": pending}), 200

@app.route("/admin/kyc/approve/<phone>", methods=["POST"])
def admin_approve(phone):
    approve_kyc(phone)
    return jsonify({"status": "approved", "phone": phone}), 200

@app.route("/admin/kyc/reject/<phone>", methods=["POST"])
def admin_reject(phone):
    reason = request.json.get("reason", "") if request.json else ""
    reject_kyc(phone, reason)
    return jsonify({"status": "rejected", "phone": phone}), 200


@app.errorhandler(500)
def handle_500(e):
    print(f"500 ERROR: {e}")
    return jsonify({"error": "Internal server error", "status": "error"}), 500

@app.errorhandler(404)
def handle_404(e):
    return jsonify({"error": "Not found", "status": "error"}), 404

@app.route("/health", methods=["GET"])
def health():
    ai_status = "connected" if GROQ_API_KEY else "no_key"
    return jsonify({"status": "ok", "service": "ZakaPay API", "version": "5.0", "ai": ai_status, "features": ["escrow", "kyc-first", "cross-border"]}), 200

@app.route("/", methods=["GET"])
def home():
    return jsonify({"service": "ZakaPay API", "version": "5.0", "status": "running"}), 200

@app.route("/compare", methods=["GET"])
def compare():
    return render_template("compare.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

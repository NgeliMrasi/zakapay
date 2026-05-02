#!/usr/bin/env python3
"""
ZakaPay — ZARC Bank Simulation Commands
deposit, withdraw, balance, send ZARC
"""

import json
import requests
import time
from stellar_sdk import Keypair, Server, TransactionBuilder, Network, Asset

HORIZON = "https://horizon-testnet.stellar.org"
NETWORK = Network.TESTNET_NETWORK_PASSPHRASE
DB_FILE = "/data/data/com.termux/files/home/ZakaPay-project/users.json"
ZARC_FILE = "/data/data/com.termux/files/home/ZakaPay-project/zarc.json"
server = Server(horizon_url=HORIZON)


def load_zarc():
    with open(ZARC_FILE, "r") as f:
        return json.load(f)


def load_users():
    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_zarc_asset():
    zarc = load_zarc()
    return Asset(zarc["asset_code"], zarc["issuer_public"])


def get_zarc_balance(public_key):
    zarc = load_zarc()
    try:
        resp = requests.get(f"{HORIZON}/accounts/{public_key}")
        if resp.status_code == 200:
            for bal in resp.json()["balances"]:
                if (bal.get("asset_code") == "ZARC" and
                    bal.get("asset_issuer") == zarc["issuer_public"]):
                    return float(bal["balance"])
    except:
        pass
    return 0.0


def get_xlm_balance(public_key):
    try:
        resp = requests.get(f"{HORIZON}/accounts/{public_key}")
        if resp.status_code == 200:
            for bal in resp.json()["balances"]:
                if bal["asset_type"] == "native":
                    return float(bal["balance"])
    except:
        pass
    return 0.0


def find_user_by_phone(users, phone):
    # Normalize: remove spaces, dashes
    clean = phone.replace(" ", "").replace("-", "")
    for p, u in users.items():
        if p == clean:
            return p, u
    return None, None


def cmd_deposit(phone, amount_str):
    users = load_users()
    user_phone, user = find_user_by_phone(users, phone)
    if not user:
        return f"Account not found for {phone}."

    try:
        amount = float(amount_str)
        if amount <= 0:
            return "Amount must be positive."
        if amount > 50000:
            return "Maximum deposit: R50,000."
    except ValueError:
        return "Invalid amount. Example: deposit 500"

    zarc = load_zarc()
    issuer_kp = Keypair.from_secret(zarc["issuer_secret"])
    zarc_asset = get_zarc_asset()

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
        users[user_phone]["zar_balance"] = new_balance
        save_users(users)

        return (
            f"Deposit successful!\n"
            f"Amount: R{amount:,.2f}\n"
            f"Balance: R{new_balance:,.2f}\n"
            f"Tx: {resp['hash'][:16]}...\n"
            f"https://stellar.expert/explorer/testnet/tx/{resp['hash']}"
        )
    except Exception as e:
        return f"Deposit failed: {str(e)[:100]}"


def cmd_withdraw(phone, amount_str):
    users = load_users()
    user_phone, user = find_user_by_phone(users, phone)
    if not user:
        return f"Account not found for {phone}."

    try:
        amount = float(amount_str)
        if amount <= 0:
            return "Amount must be positive."
    except ValueError:
        return "Invalid amount. Example: withdraw 500"

    current_balance = get_zarc_balance(user["public_key"])
    if current_balance < amount:
        return f"Insufficient. Balance: R{current_balance:,.2f}, Requested: R{amount:,.2f}"

    zarc = load_zarc()
    user_kp = Keypair.from_secret(user["secret_encrypted"])
    zarc_asset = get_zarc_asset()

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
        users[user_phone]["zar_balance"] = new_balance
        save_users(users)

        return (
            f"Withdrawal successful!\n"
            f"Amount: R{amount:,.2f}\n"
            f"Balance: R{new_balance:,.2f}\n"
            f"Tx: {resp['hash'][:16]}...\n"
            f"Funds in bank account in 1-2 days.\n"
            f"https://stellar.expert/explorer/testnet/tx/{resp['hash']}"
        )
    except Exception as e:
        return f"Withdrawal failed: {str(e)[:100]}"


def cmd_balance(phone):
    users = load_users()
    user_phone, user = find_user_by_phone(users, phone)
    if not user:
        return f"Account not found for {phone}."

    zarc_balance = get_zarc_balance(user["public_key"])
    xlm_balance = get_xlm_balance(user["public_key"])

    users[user_phone]["zar_balance"] = zarc_balance
    save_users(users)

    return (
        f"{user['name']}'s Balances\n\n"
        f"Rands (ZARC): R{zarc_balance:,.2f}\n"
        f"XLM: {xlm_balance:,.2f}\n"
        f"1 ZARC = R1.00"
    )


def cmd_send_zarc(from_phone, to_phone, amount_str):
    users = load_users()
    sender_phone, sender = find_user_by_phone(users, from_phone)
    receiver_phone, receiver = find_user_by_phone(users, to_phone)

    if not sender:
        return f"Your account not found ({from_phone})."
    if not receiver:
        return f"Recipient {to_phone} not registered. They need to register first."

    try:
        amount = float(amount_str)
        if amount <= 0:
            return "Amount must be positive."
    except ValueError:
        return "Invalid amount."

    zarc_balance = get_zarc_balance(sender["public_key"])
    if zarc_balance < amount:
        return f"Insufficient. Balance: R{zarc_balance:,.2f}, Sending: R{amount:,.2f}"

    sender_kp = Keypair.from_secret(sender["secret_encrypted"])
    zarc_asset = get_zarc_asset()

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

        new_sender_balance = get_zarc_balance(sender["public_key"])
        new_receiver_balance = get_zarc_balance(receiver["public_key"])

        users[sender_phone]["zar_balance"] = new_sender_balance
        users[receiver_phone]["zar_balance"] = new_receiver_balance
        save_users(users)

        return (
            f"Sent!\n"
            f"Amount: R{amount:,.2f}\n"
            f"To: {receiver['name']} ({to_phone})\n"
            f"Fee: R0.00 (testnet)\n"
            f"Your Balance: R{new_sender_balance:,.2f}\n"
            f"Tx: {resp['hash'][:16]}...\n"
            f"https://stellar.expert/explorer/testnet/tx/{resp['hash']}"
        )
    except Exception as e:
        return f"Transfer failed: {str(e)[:100]}"


# ─── Command Parser ───

def handle_zarc_command(message, phone):
    msg = message.strip().lower()
    raw = message.strip()

    # balance / bal / zar / rands
    if msg in ["balance", "bal", "zar", "rands", "zar balance", "rand balance"]:
        return cmd_balance(phone)

    # deposit 500 / deposit r500
    if msg.startswith("deposit"):
        parts = msg.replace("r", "").replace(",", "").split()
        if len(parts) >= 2:
            return cmd_deposit(phone, parts[1])
        return "Usage: deposit 500"

    # withdraw 500 / withdraw r500
    if msg.startswith("withdraw"):
        parts = msg.replace("r", "").replace(",", "").split()
        if len(parts) >= 2:
            return cmd_withdraw(phone, parts[1])
        return "Usage: withdraw 500"

    # send 250 +27xxx / send r250 +27xxx
    if msg.startswith("send"):
        parts = raw.replace(",", "").split()
        # Normalize: remove 'r' or 'R' prefix from amount
        clean_parts = []
        for p in parts:
            if p.lower().startswith("r") and len(p) > 1 and p[1:].replace(".", "").isdigit():
                clean_parts.append(p[1:])
            else:
                clean_parts.append(p)

        if len(clean_parts) >= 3:
            amount = clean_parts[1]
            to_phone = clean_parts[2]
            if not to_phone.startswith("+"):
                to_phone = "+" + to_phone
            return cmd_send_zarc(phone, to_phone, amount)
        return "Usage: send 250 +27820000002"

    return None


# ─── Test Mode ───

if __name__ == "__main__":
    print("=" * 50)
    print("  ZakaPay — ZARC Command Tester")
    print("=" * 50)
    print("\n  Registered users:")
    print("    +27820000001  Thabo")
    print("    +27820000002  Naledi")
    print("    +27648782381  Ngeli")
    print("    +27820000005  Zanele")
    print("\n  Commands:")
    print("    balance              Check ZARC + XLM balance")
    print("    deposit 500          Simulate bank deposit R500")
    print("    withdraw 500         Simulate bank withdrawal R500")
    print("    send 250 +27xxx      Send R250 ZARC to another user")
    print("    quit                 Exit")
    print("=" * 50)

    while True:
        print()
        msg = input("You: ").strip()
        if msg.lower() in ["quit", "exit", "q"]:
            break

        phone = input("Your phone (+27xxx): ").strip()
        if not phone.startswith("+"):
            phone = "+" + phone

        result = handle_zarc_command(msg, phone)
        if result:
            print(f"\nZakaPay:\n{result}")
        else:
            print("Unknown command. Try: balance, deposit 500, withdraw 500, send 250 +27xxx")

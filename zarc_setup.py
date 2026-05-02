#!/usr/bin/env python3
"""
ZakaPay — ZARC Stablecoin Setup
Creates ZARC asset on Stellar testnet.
Issues ZARC to user accounts.
Creates ZARC/XLM liquidity pool on Stellar DEX.
"""

import json
import requests
import time
from stellar_sdk import Keypair, Server, TransactionBuilder, Network, Asset, LiquidityPoolAsset

HORIZON = "https://horizon-testnet.stellar.org"
FRIENDBOT = "https://friendbot.stellar.org"
NETWORK = Network.TESTNET_NETWORK_PASSPHRASE
DB_FILE = "/data/data/com.termux/files/home/ZakaPay-project/users.json"
ZARC_FILE = "/data/data/com.termux/files/home/ZakaPay-project/zarc.json"
server = Server(horizon_url=HORIZON)


def fund_account(keypair):
    resp = requests.get(FRIENDBOT, params={"addr": keypair.public_key})
    if resp.status_code == 200:
        print(f"  Funded: {keypair.public_key[:12]}...")
        return True
    print(f"  Already funded or failed: {keypair.public_key[:12]}...")
    return False


def setup_zarc():
    print("=" * 50)
    print("  ZakaPay — ZARC Stablecoin Setup")
    print("  Building the Rand on Stellar")
    print("=" * 50)

    # Step 1: Create ZARC Issuer
    print("\n[1/6] Creating ZARC Issuer account...")
    issuer_kp = Keypair.random()
    fund_account(issuer_kp)
    time.sleep(3)

    # Step 2: Create ZARC Distribution Account
    print("\n[2/6] Creating ZARC Distribution account...")
    dist_kp = Keypair.random()
    fund_account(dist_kp)
    time.sleep(3)

    # Step 3: Define ZARC Asset
    print("\n[3/6] Defining ZARC asset...")
    zarc = Asset("ZARC", issuer_kp.public_key)
    print(f"  Asset: ZARC")
    print(f"  Issuer: {issuer_kp.public_key[:12]}...")
    print(f"  1 ZARC = R1.00")

    # Step 4: Trust ZARC from Distribution Account
    print("\n[4/6] Setting up trust line for ZARC...")
    try:
        dist_account = server.load_account(dist_kp.public_key)
        tx = (
            TransactionBuilder(dist_account, NETWORK, 100)
            .append_change_trust_op(asset=zarc, limit="1000000")
            .set_timeout(30)
            .build()
        )
        tx.sign(dist_kp)
        resp = server.submit_transaction(tx)
        print(f"  Trust line created: {resp['hash'][:16]}...")
    except Exception as e:
        print(f"  Error: {e}")
        return None

    # Step 5: Issue ZARC to Distribution Account
    print("\n[5/6] Issuing 1,000,000 ZARC...")
    try:
        issuer_account = server.load_account(issuer_kp.public_key)
        tx = (
            TransactionBuilder(issuer_account, NETWORK, 100)
            .append_payment_op(
                destination=dist_kp.public_key,
                amount="1000000",
                asset=zarc
            )
            .set_timeout(30)
            .build()
        )
        tx.sign(issuer_kp)
        resp = server.submit_transaction(tx)
        print(f"  Issued: {resp['hash'][:16]}...")
        print(f"  Amount: 1,000,000 ZARC (R1,000,000)")
    except Exception as e:
        print(f"  Error: {e}")
        return None

    # Step 6: Create Liquidity Pool (ZARC/XLM)
    print("\n[6/6] Creating ZARC/XLM liquidity pool on Stellar DEX...")
    lp_id = None
    try:
        # Fee 30 = 0.3%
        lp_asset = LiquidityPoolAsset(
            asset_a=Asset.native(),
            asset_b=zarc,
            fee=30
        )
        lp_id = lp_asset.liquidity_pool_id

        # Trust the LP asset
        dist_account = server.load_account(dist_kp.public_key)
        tx = (
            TransactionBuilder(dist_account, NETWORK, 100)
            .append_change_trust_op(asset=lp_asset)
            .set_timeout(30)
            .build()
        )
        tx.sign(dist_kp)
        resp = server.submit_transaction(tx)
        print(f"  LP trust line: {resp['hash'][:16]}...")

        # Deposit liquidity: 5000 XLM + 5000 ZARC
        time.sleep(3)
        dist_account = server.load_account(dist_kp.public_key)
        tx = (
            TransactionBuilder(dist_account, NETWORK, 100)
            .append_liquidity_pool_deposit_op(
                liquidity_pool_id=lp_id,
                max_amount_a="5000",
                max_amount_b="5000",
                min_price="0.5",
                max_price="2.0"
            )
            .set_timeout(30)
            .build()
        )
        tx.sign(dist_kp)
        resp = server.submit_transaction(tx)
        print(f"  Pool funded: {resp['hash'][:16]}...")
        print(f"  Liquidity: 5,000 XLM + 5,000 ZARC")
    except Exception as e:
        print(f"  Pool error: {e}")
        print(f"  Continuing without pool (can add later)...")

    # Save ZARC Configuration
    zarc_config = {
        "asset_code": "ZARC",
        "issuer_public": issuer_kp.public_key,
        "issuer_secret": issuer_kp.secret,
        "distribution_public": dist_kp.public_key,
        "distribution_secret": dist_kp.secret,
        "liquidity_pool_id": lp_id,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "supply": "1000000",
        "peg": "1 ZARC = R1.00"
    }

    with open(ZARC_FILE, "w") as f:
        json.dump(zarc_config, f, indent=2)

    print("\n" + "=" * 50)
    print("  ZARC SETUP COMPLETE")
    print("=" * 50)
    print(f"  Asset: ZARC")
    print(f"  Issuer: {issuer_kp.public_key}")
    print(f"  Distribution: {dist_kp.public_key}")
    print(f"  Supply: 1,000,000 ZARC")
    print(f"  Peg: 1 ZARC = R1.00")
    if lp_id:
        print(f"  Pool ID: {lp_id[:16]}...")
    print(f"  Config saved: {ZARC_FILE}")
    print("=" * 50)

    return zarc_config


def setup_user_trust(zarc_config, user_secret, user_name):
    kp = Keypair.from_secret(user_secret)
    zarc = Asset(zarc_config["asset_code"], zarc_config["issuer_public"])
    try:
        account = server.load_account(kp.public_key)
        tx = (
            TransactionBuilder(account, NETWORK, 100)
            .append_change_trust_op(asset=zarc, limit="100000")
            .set_timeout(30)
            .build()
        )
        tx.sign(kp)
        resp = server.submit_transaction(tx)
        print(f"  {user_name}: Trust line created ({resp['hash'][:16]}...)")
        return True
    except Exception as e:
        print(f"  {user_name}: Error - {e}")
        return False


def issue_zarc_to_user(zarc_config, user_public, amount, user_name):
    issuer_kp = Keypair.from_secret(zarc_config["issuer_secret"])
    zarc = Asset(zarc_config["asset_code"], zarc_config["issuer_public"])
    try:
        issuer_account = server.load_account(issuer_kp.public_key)
        tx = (
            TransactionBuilder(issuer_account, NETWORK, 100)
            .add_text_memo(f"ZakaPay:BankDeposit:{user_name}")
            .append_payment_op(
                destination=user_public,
                amount=str(amount),
                asset=zarc
            )
            .set_timeout(30)
            .build()
        )
        tx.sign(issuer_kp)
        resp = server.submit_transaction(tx)
        print(f"  {user_name}: R{amount} deposited ({resp['hash'][:16]}...)")
        return resp["hash"]
    except Exception as e:
        print(f"  {user_name}: Error - {e}")
        return None


def setup_all_users(zarc_config):
    print("\n" + "=" * 50)
    print("  Setting up ZARC for all users")
    print("=" * 50)

    with open(DB_FILE, "r") as f:
        users = json.load(f)

    for phone, user in users.items():
        name = user["name"]
        print(f"\n  Setting up {name} ({phone})...")
        setup_user_trust(zarc_config, user["secret_encrypted"], name)
        time.sleep(2)
        issue_zarc_to_user(zarc_config, user["public_key"], "10000", name)
        time.sleep(2)

    print("\n" + "=" * 50)
    print("  ALL USERS SET UP WITH ZARC")
    print("=" * 50)


if __name__ == "__main__":
    config = setup_zarc()
    if config:
        setup_all_users(config)

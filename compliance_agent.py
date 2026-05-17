#!/usr/bin/env python3
"""ZakaPay SARB Compliance Agent"""

import json
import os
from datetime import datetime

DAILY_LIMIT = 10000.00
MONTHLY_LIMIT = 1000000.00
SINGLE_TX_ALERT = 5000.00
DB_FILE = os.path.expanduser("~/ZakaPay-project/users.json")

def load_users():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def generate_report():
    users = load_users()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    this_month = datetime.now().strftime("%Y-%m")
    today = datetime.now().strftime("%Y-%m-%d")

    monthly_total = 0
    monthly_count = 0
    daily_alerts = []
    suspicious = []
    recent_txs = []
    daily_totals = {}

    for phone, user in users.items():
        name = user.get("name", "Unknown")
        for tx in user.get("transactions", []):
            if tx.get("type") == "crossborder" and tx.get("status") == "confirmed":
                amount = float(tx.get("amount", 0))
                tx_date = tx.get("timestamp", "")[:10]
                tx_month = tx.get("timestamp", "")[:7]

                # Monthly totals
                if tx_month == this_month:
                    monthly_total += amount
                    monthly_count += 1

                # Daily limits
                if tx_date == today:
                    if phone not in daily_totals:
                        daily_totals[phone] = {"name": name, "total": 0}
                    daily_totals[phone]["total"] += amount

                # Large transaction flag
                if amount > SINGLE_TX_ALERT:
                    suspicious.append(f"  FLAG: Large tx R{amount:,.2f} by {name} ({phone})")

                recent_txs.append(f"  {tx.get('timestamp', 'N/A')[:16]} | {name} | R{amount:,.2f} | {tx.get('destination', 'N/A')} | {tx.get('status', 'N/A')}")

    # Daily limit checks
    for phone, data in daily_totals.items():
        if data["total"] > DAILY_LIMIT:
            daily_alerts.append(f"  ALERT: {data['name']} ({phone}) exceeded R{DAILY_LIMIT:,.2f} daily limit: R{data['total']:,.2f}")

    remaining = MONTHLY_LIMIT - monthly_total
    status = "WITHIN LIMITS" if monthly_total < MONTHLY_LIMIT else "EXCEEDED"

    report = f"""
ZAKAPAY SARB COMPLIANCE REPORT
Generated: {now}
==================================================

MONTHLY SUMMARY
  Transactions: {monthly_count}
  Volume: R{monthly_total:,.2f}
  Sandbox limit: R{MONTHLY_LIMIT:,.2f}
  Remaining: R{remaining:,.2f}
  Status: {status}

DAILY LIMIT CHECKS
"""
    report += "\n".join(daily_alerts) if daily_alerts else "  No breaches"

    report += "\n\nSUSPICIOUS PATTERNS\n"
    report += "\n".join(suspicious) if suspicious else "  No flags"

    report += "\n\nRECENT CROSS-BORDER TRANSACTIONS\n"
    report += "\n".join(recent_txs[-10:]) if recent_txs else "  No transactions yet"

    report += "\n\n=================================================="
    report += "\nEND OF REPORT"

    return report

if __name__ == "__main__":
    print(generate_report())

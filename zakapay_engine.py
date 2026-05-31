import os
import json
from datetime import datetime

# =====================================================================
# 1. LIVE SCHEMA ENVIRONMENT (Matches ZakaPay_KYC_Schema_SA_ZW.md)
# =====================================================================
# This mimics your internal user database record (Tier 2 Verified)
MOCK_INTERNAL_KYC_DB = {
    "sender_id": "zk-user-880412",
    "first_name": "Ngeli",
    "last_name": "Mrasi",
    "sa_id_type": "SA ID",
    "sa_id_number": "880412XXXXXXX",
    "phone_number": "+27648782381",
    "street": "142 Albert Road",
    "postal_code": "7925",
    "city": "Cape Town",
    "country_code": "ZA",
    "sender_stellar_pubkey": "GBCXT...ZEAM_READY_KEY"
}

# =====================================================================
# 2. IVMS 101 COMPLIANCE PAYLOAD TRANSLATOR (The Travel Rule Engine)
# =====================================================================
def generate_ivms101_payload(sender_data, parsed_intent, beneficiary_id_type=None, beneficiary_id_num=None):
    """
    Translates ZakaPay's internal WhatsApp data into the globally accepted
    InterVASP Messaging Standard (IVMS 101) required by institutional anchors.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Enforce conditional rule values if not provided by step-up prompt
    id_type = beneficiary_id_type if beneficiary_id_type else "NOT_REQUIRED"
    id_num = beneficiary_id_num if beneficiary_id_num else "NOT_REQUIRED"
    
    ivms101_payload = {
        "tx_metadata": {
            "zakapay_tx_id": f"zk-tx-{int(datetime.utcnow().timestamp())}",
            "timestamp_utc": timestamp,
            "network": "stellar_mainnet",
            "settlement_currency": "SARZ" # Zeam's settlement stablecoin asset
        },
        "originator": {
            "natural_person": {
                "name": {
                    "given_name": sender_data["first_name"],
                    "primary_identifier": sender_data["last_name"]
                },
                "geographic_address": {
                    "address_type": "HOME",
                    "street_name": sender_data["street"],
                    "post_code": sender_data["postal_code"],
                    "town_name": sender_data["city"],
                    "country": sender_data["country_code"]
                },
                "national_identification": {
                    "national_identifier": sender_data["sa_id_number"],
                    "national_identifier_type": "NIDN", # National Identity Number
                    "registration_country": sender_data["country_code"]
                }
            },
            "account_number": [sender_data["sender_stellar_pubkey"]]
        },
        "beneficiary": {
            "natural_person": {
                "name": {
                    "given_name": parsed_intent.get("recipient_first_name", "Unknown"),
                    "primary_identifier": parsed_intent.get("recipient_last_name", "Unknown")
                },
                "national_identification": {
                    "national_identifier": id_num,
                    "national_identifier_type": "NIDN" if id_type == "Zimbabwe National ID" else "PASS",
                    "registration_country": "ZW"
                }
            },
            "account_number": [parsed_intent.get("recipient_phone")],
            "vasp_or_wallet_provider": parsed_intent.get("mobile_money_provider", "EcoCash_Zimbabwe")
        },
        "transfer_details": {
            "source_fiat_amount": float(parsed_intent.get("amount", 0.0)),
            "source_fiat_currency": "ZAR",
            "source_of_funds": "WAGES"
        }
    }
    return ivms101_payload

# =====================================================================
# 3. CORE PROCESSING ENGINE
# =====================================================================
def process_incoming_whatsapp(message_text):
    print(f"📥 [WhatsApp] Input: '{message_text}'")
    
    # Simulating what your Groq AI model extracts from the raw string
    mock_parsed_intent = {
        "amount": 2800.00,
        "recipient_first_name": "Tendai",
        "recipient_last_name": "Moyo",
        "recipient_phone": "26377XXXXXXX",
        "mobile_money_provider": "EcoCash_Zimbabwe"
    }
    print("🤖 [Groq AI] Intent extracted successfully.")

    # Apply the conditional validation rules from your .md file
    b_id_type = None
    b_id_num = None
    
    if mock_parsed_intent["amount"] >= 3000.00:
        print(f"⚠️ [Compliance Warning] Amount R{mock_parsed_intent['amount']} >= R3,000 threshold.")
        print("📸 Triggering Native WhatsApp Video Note Liveness + Beneficiary ID collection prompt.")
        # Simulating user response values captured via text/menu input
        b_id_type = "Zimbabwe National ID"
        b_id_num = "29-XXXXXX-X-29"
    else:
        print(f"✅ [Compliance Pass] Amount R{mock_parsed_intent['amount']} below conditional compliance cap.")
        print("📸 Active Native WhatsApp Video Note Liveness check passed.")

    # Compile data into structured, partner-ready IVMS 101 payload
    print("⚙️ [Compliance Engine] Compiling standard IVMS 101 Travel Rule schema...")
    travel_rule_package = generate_ivms101_payload(
        sender_data=MOCK_INTERNAL_KYC_DB,
        parsed_intent=mock_parsed_intent,
        beneficiary_id_type=b_id_type,
        beneficiary_id_num=b_id_num
    )
    
    # Log transaction entry to append-only file for FICA 5-year retention protocol
    audit_file = "zakapay_compliance_audit.jsonl"
    with open(audit_file, "a") as f:
        f.write(json.dumps(travel_rule_package) + "\n")
    print(f"💾 [Audit Trail] Transaction logged locally to {audit_file} (5-year retention active).")
    
    # Ready to execute POST webhook to Zeam API
    print("\n🚀 [Network Layer] Transmitting companion IVMS 101 data package to partner VASP endpoint:")
    print(json.dumps(travel_rule_package, indent=2))
    
    return travel_rule_package

if __name__ == "__main__":
    # Test case 1: Below threshold
    process_incoming_whatsapp("Send R2800 to Tendai Moyo")

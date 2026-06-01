import os
import json
from datetime import datetime, timezone

# =====================================================================
# 1. LIVE SCHEMA ENVIRONMENT (Matches ZakaPay_KYC_Schema_SA_ZW.md)
# =====================================================================
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
    InterVASP Messaging Standard (IVMS 101) using modern timezone-aware datetimes.
    """
    # Fixes DeprecationWarning by using modern timezone-aware UTC datetime
    current_time = datetime.now(timezone.utc)
    timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    id_type = beneficiary_id_type if beneficiary_id_type else "NOT_REQUIRED"
    id_num = beneficiary_id_num if beneficiary_id_num else "NOT_REQUIRED"
    
    ivms101_payload = {
        "tx_metadata": {
            "zakapay_tx_id": f"zk-tx-{int(current_time.timestamp())}",
            "timestamp_utc": timestamp,
            "network": "stellar_mainnet",
            "settlement_currency": "SARZ"
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
                    "national_identifier_type": "NIDN",
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
    
    # Simple extraction logic based on the string value for dynamic testing
    amount_value = 2800.00
    if "3500" in message_text:
        amount_value = 3500.00
        
    mock_parsed_intent = {
        "amount": amount_value,
        "recipient_first_name": "Tendai",
        "recipient_last_name": "Moyo",
        "recipient_phone": "26377XXXXXXX",
        "mobile_money_provider": "EcoCash_Zimbabwe"
    }
    print("🤖 [Groq AI] Intent extracted successfully.")

    b_id_type = None
    b_id_num = None
    
    if mock_parsed_intent["amount"] >= 3000.00:
        print(f"⚠️ [Compliance Warning] Amount R{mock_parsed_intent['amount']} >= R3,000 threshold.")
        print("📸 Triggering Native WhatsApp Video Note Liveness + Beneficiary ID collection prompt.")
        b_id_type = "Zimbabwe National ID"
        b_id_num = "29-XXXXXX-X-29"
    else:
        print(f"✅ [Compliance Pass] Amount R{mock_parsed_intent['amount']} below conditional compliance cap.")
        print("📸 Active Native WhatsApp Video Note Liveness check passed.")

    print("⚙️ [Compliance Engine] Compiling standard IVMS 101 Travel Rule schema...")
    travel_rule_package = generate_ivms101_payload(
        sender_data=MOCK_INTERNAL_KYC_DB,
        parsed_intent=mock_parsed_intent,
        beneficiary_id_type=b_id_type,
        beneficiary_id_num=b_id_num
    )
    
    audit_file = "zakapay_compliance_audit.jsonl"
    with open(audit_file, "a") as f:
        f.write(json.dumps(travel_rule_package) + "\n")
    print(f"💾 [Audit Trail] Transaction logged locally to {audit_file} (5-year retention active).")
    
    print("\n🚀 [Network Layer] Transmitting companion IVMS 101 data package to partner VASP endpoint:")
    print(json.dumps(travel_rule_package, indent=2))
    
    return travel_rule_package

if __name__ == "__main__":
    # Test case: Default to R2800
    process_incoming_whatsapp("Send R2800 to Tendai Moyo")

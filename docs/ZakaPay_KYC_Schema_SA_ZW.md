# ZakaPay × Zeam: Travel Rule / KYC Data Schema
## South Africa → Zimbabwe Corridor

---

## Overview

This document defines the sender and beneficiary data fields ZakaPay captures
inside the WhatsApp flow to satisfy Travel Rule and FICA/RBZ compliance
requirements for the SA-to-ZW remittance corridor.

ZakaPay uses AI-native intent parsing to capture these fields conversationally
inside WhatsApp. No app download. No web forms. No friction.

---

## Minimal Viable Schema (Pilot Phase)

R5,000 per-transaction cap. Single corridor SA to ZW.

### Sender (South Africa — FICA)

| Field | Type | Required | Capture Method |
|-------|------|----------|----------------|
| First Name | String | Yes | WhatsApp text |
| Last Name | String | Yes | WhatsApp text |
| SA ID Number | String (13 digits) | Yes | WhatsApp text |
| Phone Number | String (+27) | Auto | Twilio inbound |
| Selfie Photo | Image | Yes | WhatsApp image |
| ID Document Photo | Image | Yes | WhatsApp image |

### Beneficiary (Zimbabwe — RBZ)

| Field | Type | Required | Capture Method |
|-------|------|----------|----------------|
| Full Name | String | Yes | WhatsApp text |
| Phone Number | String (+263) | Yes | WhatsApp text |
| Mobile Money Provider | Enum | Yes | WhatsApp selection |
| Beneficiary ID Type | Enum | Conditional | WhatsApp menu |
| Beneficiary ID Number | String | Conditional | WhatsApp text |

Provider options:
- EcoCash
- OneMoney
- InnBucks

Beneficiary ID rules:
- Transactions below R3,000: ID optional
- Transactions R3,000 and above: ID required
- ID types: Zimbabwe National ID, Passport, Driver's License

---

## Full Production Schema

All pilot fields plus:

### Sender (Additional)

| Field | Type | Required | Capture Method |
|-------|------|----------|----------------|
| Physical Address | String | Yes | WhatsApp text |
| Date of Birth | Date | Yes | Parsed from ID |
| Source of Funds | Enum | Yes | WhatsApp menu |
| Occupation | String | Yes | WhatsApp text |

Source of Funds options:
- Employment salary
- Business income
- Savings
- Pension
- Other (specify)

### Beneficiary (Additional)

| Field | Type | Required | Capture Method |
|-------|------|----------|----------------|
| Relationship to Sender | Enum | Yes | WhatsApp menu |

Relationship options:
- Spouse
- Parent
- Child
- Sibling
- Other family
- Business partner
- Other

---

## Travel Rule Data Exchange (FATF Compliant)

ZakaPay transmits originator and beneficiary data alongside every transaction.
Data format: JSON payload attached to Stellar memo field.

### Originator Data (Sender)
- full_name
- id_type (SA ID / Passport)
- id_number
- phone_number
- physical_address

### Beneficiary Data (Recipient)
- full_name
- phone_number
- id_type (conditional: required above R3,000)
- id_number (conditional: required above R3,000)
- mobile_money_provider
- mobile_money_account

### Transmission Method
- Data attached to Stellar transaction memo (JSON-encoded)
- Companion data shared via API endpoint to receiving VASP
- Retained in ZakaPay audit log for 5 years (FICA requirement)

---

## Data Retention and Audit Export

- Retention period: 5 years (FICA requirement)
- Export formats: CSV, JSON
- Export triggers: Manual (WhatsApp command) or scheduled (monthly)
- SARB sandbox reporting: Structured JSON export with full tx metadata
- Fields exported: timestamp, sender, beneficiary, amount, fee, FX rate, tx hash, compliance checks

---

## AI Compliance Agent Integration

ZakaPay compliance agent runs the following checks automatically:

1. FICA Verification — SA ID number validated against checksum
2. Sanctions Screening — Names checked against OFAC and UN sanctions lists
3. Transaction Monitoring — R5,000 per-tx cap enforced
4. Daily Limits — R10,000 per sender per day flagged
5. Monthly Limits — R1,000,000 total volume tracked
6. Pattern Detection — Rapid successive transactions flagged
7. Audit Trail — All transactions logged with timestamps for SARB reporting

---

## Data Flow

WhatsApp Message
  -> Twilio Webhook
  -> ZakaPay AI Intent Parser
  -> KYC Field Extraction
  -> Compliance Agent Checks
  -> Zeam API (sender + beneficiary data)
  -> Stellar Ledger (on-chain settlement)
  -> Confirmation to Sender (WhatsApp)

---

## Notes

- All data captured conversationally inside WhatsApp
- No app download required from sender or beneficiary
- Selfie + ID captured via WhatsApp image message
- AI parser extracts fields from natural text input
- Liveness check: Video note verification (WhatsApp native) for pilot
- Beneficiary ID: Required for transactions R3,000 and above
- Compliance checks run in real-time before transaction submission
- Full audit trail exportable for SARB sandbox reporting

---

Prepared by: ZakaPay Africa Technologies
Date: May 2026
Contact: ngeli@zakapay.africa

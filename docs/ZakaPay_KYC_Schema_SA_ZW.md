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

Provider options:
- EcoCash
- OneMoney
- InnBucks

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
- Compliance checks run in real-time before transaction submission
- Full audit trail exportable for SARB sandbox reporting

---

Prepared by: ZakaPay Africa Technologies
Date: May 2026
Contact: ngeli@zakapay.africa

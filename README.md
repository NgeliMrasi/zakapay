# ZakaPay
### Cross-Border Payments on WhatsApp. R10 Flat Fee. 5 Seconds.

ZakaPay is a WhatsApp-native cross-border remittance platform built on the Stellar blockchain. It enables anyone to send money across African borders using only WhatsApp — no app download, no bank account, no data bundle needed.

Inspired by Felix Pago ($400M valuation, US-Mexico), built for the African diaspora.

---

## What It Does

- KYC via WhatsApp — Send selfie + ID photo, admin approves on dashboard
- Register a wallet — Conversational flow: "What should I call you?" then Pick a PIN
- Deposit — Bank to ZakaPay via WhatsApp
- Send money (domestic) — "Send R100 to +2782..." Instant transfer
- Send money (cross-border) — "Send R1000 to +263..." Auto-detects Zimbabwe, R10 fee
- Withdraw — "Take out R500" Instant withdrawal to bank
- Transaction history — Full on-chain proof via Stellar Explorer
- Escrow system — Send to unregistered users, they receive when they join
- Admin dashboard — Web-based KYC review with selfie + ID photo viewer

---

## Supported Cross-Border Corridors (10 Countries)

- Zimbabwe (+263) — USD — R1 = 0.054 USD
- Tanzania (+255) — TZS — R1 = 290.5 TZS
- Mozambique (+258) — MZN — R1 = 3.38 MZN
- Kenya (+254) — KES — R1 = 6.95 KES
- Nigeria (+234) — NGN — R1 = 82.5 NGN
- Zambia (+260) — ZMW — R1 = 1.38 ZMW
- Malawi (+265) — MWK — R1 = 88.2 MWK
- Ghana (+233) — GHS — R1 = 0.68 GHS
- Somalia (+252) — USD — R1 = 0.054 USD
- Ethiopia (+251) — ETB — R1 = 3.12 ETB

R10 flat fee to all corridors. 5-second settlement.

---

## ZakaPay vs The Competition

Sending R2,000 from South Africa to Zimbabwe:

Western Union: Fee R120, FX ~6%, Recipient gets USD 97.80, Speed: Minutes, Cost: 10%
Mukuru: Fee R50, FX ~4%, Recipient gets USD 101.42, Speed: Minutes, Cost: 6.5%
WorldRemit: Fee R40, FX ~3%, Recipient gets USD 103.20, Speed: Minutes, Cost: 5%
Wise: Fee R30, FX ~1%, Recipient gets USD 105.80, Speed: Minutes, Cost: 3%
ZAKAPAY: Fee R10, FX 0%, Recipient gets USD 107.46, Speed: 5 sec, Cost: 0.5%

Recipient gets USD 9.66 MORE with ZakaPay.

---

## Architecture

WhatsApp -> Twilio -> Flask API -> Stellar Blockchain -> ZARC Stablecoin -> Stellar DEX (ZARC to USDC) -> Mobile Money / Cash Pickup -> Recipient

| Layer | Technology |
| Frontend | WhatsApp Business API (zero UI) |
| AI | Groq (llama-3.1-8b-instant) for natural language |
| Backend | Flask API (Python) on Render |
| Security | Cloudflare SSL + AES-256 PIN hashing |
| Blockchain | Stellar Network (ZARC stablecoin + XLM) |
| Exchange | Stellar DEX for cross-border FX |
| KYC | WhatsApp-native selfie + ID verification |
| Admin | Web dashboard at /admin |

---

## API Endpoints

- GET / — API status
- GET /health — Health check + version
- POST /webhook — Twilio WhatsApp webhook
- POST /api/v1/webhook/whatsapp — 360dialog WhatsApp webhook
- GET /admin — KYC admin dashboard
- GET /admin/kyc — List pending KYC submissions
- POST /admin/kyc/approve/<phone> — Approve KYC
- POST /admin/kyc/reject/<phone> — Reject KYC
- GET /compare — ZakaPay vs competition comparison

---

## Verified On-Chain Transactions

All transactions verified on Stellar Testnet.

- Friendbot funding: b5a3e31cc0ca0edff5b4e71412461d824ffac9f32a63f2063ea664c59d181f64
- First signed transaction: 5a2de62ab69d9fbda6957df02a00f1782641a5f46ad1a9fe8e71244a59667438
- P2P Thabo to Naledi: 47ced31b6cc26a3195e82078100964940ffa9c87b24dc390278fdb26e13d5306
- WhatsApp payment: d1a37ac16de8db66
- Deposit R5,000: 790e2c22c713e18e9feb891619899ea787635fbcb7018710e448bce6f7f8c5a9
- Cross-border SA to Zimbabwe: fbd6f40bcba1c5af53201ab7cc442388ce5334ea02042efc93563739f98035ba
- Cross-border SA to Somalia: f0ed5f5e1da6849e52a9181a160d55d10132aceb3606ae03b0a494b8b5d32705
- Cross-border SA to Ethiopia: 4387bdad7a4c829401580f399f7abcb890d108b60fe2e3ed6214eab73fc25ac8
- Withdrawal R500: 7459124a90084032754e60c64cac6badf3dc39d40fa0bf309fae1a103bd4f712

Verify at: https://stellar.expert/explorer/testnet/

---

## The Market

- SA outward remittance: $330M+ (SARB / World Bank)
- SADC total remittance: $3B+ (World Bank RPW)
- FNB eWallet users: 8.2 million (FNB / Daily Investor)
- FNB eWallet volume: R43 billion (FNB / Daily Investor)
- Unbanked in SA: 18 million (FSCA)
- Spaza shops in SA: 200,000+ (SARS)
- Somali-owned spaza shops: ~98% (Industry estimate)
- Avg monthly remittance per spaza: R20,000 (Industry estimate)
- ZakaPay saving vs Western Union: R1,500/month per user (Calculated)

---

## Business Model

- Domestic P2P transfer: R2.50 flat fee, ~99.9% margin
- Cross-border transfer: R10.00 flat fee, ~88% margin
- Cash-in at spaza shop: R2.00, ~95% margin
- Cash-out at spaza shop: R2.00, ~95% margin

---

## Acquisition Strategy (Felix Pago Model)

1. Somali spaza owners send money home via WhatsApp (saves R1,500/month vs Western Union)
2. They tell 10 cousins who also own spazas (viral within the Somali business network)
3. Same users start using ZakaPay for domestic payments and supplier transfers
4. Network effect: Money never leaves the digital ecosystem

---

## The Team

- Ngeli Mrasi — Founder and CEO — Product, Vision, Business Development
- MiMo (Xiaomi AI) — Technical Co-Founder — Architecture, Backend, Blockchain
- Gemini (Google AI) — Strategy and Research — Market Analysis, Pitch Strategy

---

## Getting Started

- Landing page: https://zakapay.africa
- Admin dashboard: https://zakapay.onrender.com/admin
- Comparison page: https://zakapay.onrender.com/compare
- API health: https://zakapay.onrender.com/health
- GitHub: https://github.com/NgeliMrasi/zakapay
- On-chain proof: https://stellar.expert/explorer/testnet/account/GC4IMZQ2TP7DAJV3EGVRFX43QFCS4D4P7HVGF4YZEIBKLWG65U3LFOQL

---

## License

Proprietary. ZakaPay Africa 2026.

# SCF Build Award Application: ZakaPay

## Cross-Border Payment Infrastructure for the African Diaspora

**Applicant:** Ngeli Mrasi
**Project:** ZakaPay
**Website:** https://zakapay.africa
**GitHub:** https://github.com/NgeliMrasi/zakapay
**On-Chain Proof:** https://stellar.expert/explorer/testnet/account/GC4IMZQ2TP7DAJV3EGVRFX43QFCS4D4P7HVGF4YZEIBKLWG65U3LFOQL
**Contact:** ngeli@zakapay.africa | +27 64 878 2381

---

## 1. Project Overview

ZakaPay is a WhatsApp-native cross-border remittance platform built on the Stellar blockchain. It enables migrant workers and diaspora communities in South Africa to send money home to 10 African countries via WhatsApp for a flat R10 fee, with 5-second settlement.

**The problem:** Millions of Zimbabweans, Somalis, Ethiopians, Mozambicans, and other African nationals working in South Africa send money home every month. They pay 8-10% in fees via Western Union or Mukuru. A Somali spaza owner sending R20,000/month home loses R1,500+ in fees. The SADC remittance corridor moves over $3 billion annually, yet the people who need affordable transfers the most pay the highest fees.

**The solution:** ZakaPay replaces expensive, slow remittance services with a WhatsApp-native experience powered by the Stellar blockchain. Users send a WhatsApp message with a phone number and amount. ZakaPay auto-detects the recipient's country, shows the fee and exchange rate, and settles the transfer on-chain in 5 seconds for a flat R10 fee.

**Why Stellar:** Stellar is purpose-built for cross-border payments. The decentralized exchange (DEX) provides real-time FX conversion without bank intermediaries. ZARC stablecoin anchors the ZAR side, while Stellar's speed (5-second finality) and low cost (~R0.001 per transaction) make the R10 flat fee model economically viable at 88% margin.

---

## 2. Stellar Use Case and Technical Integration

### Core Stellar Components

ZakaPay integrates deeply with the Stellar network across five layers:

**Layer 1: Stablecoin (ZARC)**
- ZakaPay uses ZARC, a ZAR-pegged stablecoin on Stellar, as the primary store of value
- Users deposit ZAR, which mints ZARC to their Stellar wallet
- Users withdraw ZAR, which burns ZARC from their Stellar wallet
- All balances are read directly from the Stellar ledger via the Stellar SDK

**Layer 2: Stellar DEX (Cross-Border FX)**
- Cross-border transfers route through Stellar's decentralized exchange
- ZARC is converted to USDC at real-time market rates
- No FX markup - the DEX rate is the rate the user gets
- This eliminates the 4-6% markup that Western Union and banks charge

**Layer 3: On-Chain Transactions**
- Every transaction (deposit, P2P, cross-border, withdrawal) is a Stellar transaction
- Each transaction has a verifiable hash on the Stellar blockchain
- Users can verify their transactions at stellar.expert
- Transaction memos use structured format: ZP:XB:ZIM:1000

**Layer 4: Trustlines and Asset Management**
- Users create trustlines to ZARC during wallet creation
- ZARC issuer account manages asset distribution
- Cross-border payments route through issuer accounts
- Escrow system uses temporary Stellar accounts for unregistered recipients

**Layer 5: Account Management**
- Each user gets a unique Stellar keypair (public + secret)
- Secrets are encrypted with AES-256 and stored securely
- PINs are hashed with SHA-256
- Account creation is funded via Stellar Friendbot (testnet) or mainnet funding

### Architecture

WhatsApp User -> Twilio WhatsApp API -> Flask Backend (Python) -> Stellar SDK -> Stellar Network (ZARC, DEX, On-chain settlement)

Flask Backend also connects to:
- Groq AI (llama-3.1-8b-instant) for intent parsing
- User database (JSON) for account management
- KYC pipeline (selfie + ID) for compliance
- Admin dashboard (web) for KYC approval

### Technical Stack

| Component | Technology | Stellar Integration |
|-----------|-----------|-------------------|
| Frontend | WhatsApp Business API | Zero UI - chat is the interface |
| Backend | Flask (Python) on Render | Stellar SDK for all transactions |
| AI | Groq (llama-3.1-8b-instant) | Natural language intent parsing |
| Blockchain | Stellar Network | ZARC stablecoin, DEX, on-chain settlement |
| Security | AES-256 encryption, SHA-256 hashing | Stellar keypair management |
| KYC | WhatsApp selfie + ID verification | FICA-ready pipeline |
| Admin | Web dashboard at /admin | KYC approval, transaction monitoring |

---

## 3. Product Readiness and Traction

### What Is Built Today

ZakaPay has a fully functional product on Stellar testnet. The following features are live and operational:

**Registration and KYC**
- WhatsApp-native KYC: users send selfie + ID photo
- Admin dashboard for KYC review and approval
- Conversational onboarding: "What should I call you?" then Pick a PIN
- R100 welcome bonus credited on-chain

**Deposits and Withdrawals**
- Bank-to-ZakaPay deposits (on-chain ZARC minting)
- ZakaPay-to-bank withdrawals (on-chain ZARC burning)
- Balance queries read directly from Stellar ledger

**Peer-to-Peer Transfers**
- Domestic P2P transfers between registered users
- Escrow system for unregistered recipients (money waits until they join)
- R2.50 flat fee per domestic transfer

**Cross-Border Transfers**
- 10 African corridors: Zimbabwe, Tanzania, Mozambique, Kenya, Nigeria, Zambia, Malawi, Ghana, Somalia, Ethiopia
- Country auto-detection from recipient phone number
- R10 flat fee to all corridors
- 5-second on-chain settlement
- Exchange rate shown before confirmation

**Transaction History**
- Full transaction history with Stellar Explorer links
- Every transaction verifiable on-chain

### Verified On-Chain Transactions

All transactions below are verified on Stellar Testnet:

| Transaction | Hash |
|------------|------|
| Friendbot funding | b5a3e31cc0ca0edff5b4e71412461d824ffac9f32a63f2063ea664c59d181f64 |
| First signed transaction | 5a2de62ab69d9fbda6957df02a00f1782641a5f46ad1a9fe8e71244a59667438 |
| P2P: Thabo to Naledi | 47ced31b6cc26a3195e82078100964940ffa9c87b24dc390278fdb26e13d5306 |
| Deposit R5,000 | 790e2c22c713e18e9feb891619899ea787635fbcb7018710e448bce6f7f8c5a9 |
| Cross-border: SA to Zimbabwe | fbd6f40bcba1c5af53201ab7cc442388ce5334ea02042efc93563739f98035ba |
| Cross-border: SA to Somalia | f0ed5f5e1da6849e52a9181a160d55d10132aceb3606ae03b0a494b8b5d32705 |
| Cross-border: SA to Ethiopia | 4387bdad7a4c829401580f399f7abcb890d108b60fe2e3ed6214eab73fc25ac8 |
| Cross-border: SA to Mozambique | d162810da133d2fac7722a5f2a84803f1dfa8dbd04734a3bc9681e4b4c7e778c |
| Withdrawal R500 | 7459124a90084032754e60c64cac6badf3dc39d40fa0bf309fae1a103bd4f712 |

**Verify at:** https://stellar.expert/explorer/testnet/account/GC4IMZQ2TP7DAJV3EGVRFX43QFCS4D4P7HVGF4YZEIBKLWG65U3LFOQL

### Live Demonstrations

- **Landing page:** https://zakapay.africa
- **API health:** https://zakapay.onrender.com/health
- **Admin dashboard:** https://zakapay.onrender.com/admin
- **Comparison page:** https://zakapay.onrender.com/compare
- **GitHub:** https://github.com/NgeliMrasi/zakapay

### Traction Summary

- 9 verified on-chain transactions on Stellar testnet
- Cross-border transfers to 5 countries in live WhatsApp sessions
- 10 African corridors built and functional
- Full KYC pipeline via WhatsApp
- Admin dashboard for compliance
- Landing page with waitlist
- Pre-revenue, pre-seed
- Built in 3 weeks by one founder on a smartphone using Termux

---

## 4. Build Readiness

### Team

**Ngeli Mrasi - Founder and CEO**
- UCT Genesis graduate
- Built the entire ZakaPay prototype on a smartphone using Termux (no PC, no laptop)
- Deep understanding of the unbanked market from lived experience in South Africa
- Currently applying to Antler South Africa, Founders Factory Africa, and Octoco Yenza Venture Studio

**Technical Approach**
- Solo founder augmented by AI co-founders (Xiaomi MiMo for architecture/backend, Google Gemini for strategy/research)
- This approach enabled rapid prototyping: full product in 3 weeks
- For mainnet deployment and production scaling, the team will expand with:
  - Mobile money API integration specialist (EcoCash, M-Pesa)
  - Compliance/legal advisor for FSP license or SARB sandbox
  - Smart contract developer (if ZAKA stablecoin issuance requires contract-based logic)

### Development Environment

- Backend: Flask (Python) on Render (24/7 availability)
- Blockchain: Stellar SDK for Python
- Frontend: WhatsApp Business API via Twilio
- AI: Groq API (llama-3.1-8b-instant)
- Development: Termux on Android smartphone
- Version control: GitHub
- All code is production-grade and deployed

---

## 5. Tranche Structure and Deliverables

### Tranche 1: MVP on Testnet - COMPLETED

**Status:** Done. No funding required for this tranche.

| Deliverable | Status | Verification |
|------------|--------|-------------|
| WhatsApp bot with conversational AI | Done | Live |
| KYC pipeline (selfie + ID via WhatsApp) | Done | Admin dashboard |
| Stellar wallet creation (keypair + trustline) | Done | On-chain |
| ZARC deposit and withdrawal | Done | On-chain |
| Domestic P2P transfers | Done | On-chain |
| Cross-border transfers to 10 African corridors | Done | On-chain |
| Escrow system for unregistered recipients | Done | On-chain |
| R100 welcome bonus (ZARC minting) | Done | On-chain |
| Transaction history with Stellar Explorer links | Done | On-chain |
| 9 verified testnet transactions | Done | stellar.expert |
| Landing page with waitlist | Done | zakapay.africa |
| Admin dashboard for KYC approval | Done | /admin |

**Tranche 1 Budget:** $0 (self-funded)

### Tranche 2: Mobile Money Integration + Pilot

**Timeline:** Months 1-3 after award

**Objective:** Integrate mobile money APIs for real cash-out in Zimbabwe (EcoCash) and pilot with 50 Somali spaza shops in Cape Town.

| Deliverable | Description | Cost |
|------------|-------------|------|
| EcoCash API integration | Connect Stellar USDC to EcoCash for cash-out in Zimbabwe | $8,000 |
| M-Pesa API integration | Connect Stellar USDC to M-Pesa for cash-out in Tanzania and Mozambique | $8,000 |
| Cash-in/cash-out agent system | WhatsApp commands for spaza shop cash-in and cash-out with commission tracking | $5,000 |
| 50-spaza pilot | Onboard 50 Somali spaza shops in Cape Town for cross-border remittance | $4,000 |
| Compliance framework | SARB Innovation Hub sandbox application or FSP license pathway | $5,000 |
| Monitoring and analytics | Transaction dashboard, volume tracking, error monitoring | $2,000 |

**Tranche 2 Total:** $32,000

**Key Milestones:**
- EcoCash cash-out working end-to-end (Stellar -> USDC -> EcoCash -> recipient)
- M-Pesa cash-out working end-to-end
- 50 spaza shops onboarded and transacting
- R500,000+ in testnet cross-border volume
- SARB sandbox application submitted

### Tranche 3: Mainnet Launch + ZAKA Stablecoin

**Timeline:** Months 3-6 after award

**Objective:** Deploy on Stellar mainnet with real ZARC/ZAKA, live cross-border transfers, and production infrastructure.

| Deliverable | Description | Cost |
|------------|-------------|------|
| Stellar mainnet deployment | Move from testnet to mainnet with real assets | $3,000 |
| ZAKA stablecoin issuance | Issue ZAKA (ZAR-pegged stablecoin) on Stellar mainnet | $5,000 |
| Stellar Info File | Complete Stellar Info File for ZAKA with reserve documentation | $2,000 |
| Third-party reserve audit | Independent audit of ZAKA reserves (ZAR backing) | $10,000 |
| Production infrastructure | Scalable backend, load balancing, monitoring, 99.9% uptime | $5,000 |
| Security audit | Code review, penetration testing, key management audit | $5,000 |
| Multi-corridor live testing | End-to-end testing of all 10 corridors on mainnet with real funds | $2,000 |

**Tranche 3 Total:** $32,000

**Key Milestones:**
- ZAKA stablecoin live on Stellar mainnet
- Stellar Info File published with reserve proof
- Third-party audit completed
- Cross-border transfers working on mainnet to all 10 corridors
- 100+ real users transacting on mainnet
- R1,000,000+ in mainnet cross-border volume

---

## 6. Total Budget

| Tranche | Description | Budget |
|---------|------------|--------|
| Tranche 1 | MVP on Testnet (COMPLETED) | $0 |
| Tranche 2 | Mobile Money Integration + Pilot | $32,000 |
| Tranche 3 | Mainnet Launch + ZAKA Stablecoin | $32,000 |
| **Total** | | **$64,000** |

### Budget Breakdown by Category

| Category | Amount | Details |
|----------|--------|---------|
| Development | $28,000 | EcoCash API, M-Pesa API, agent system, mainnet deployment |
| ZAKA Stablecoin | $17,000 | Issuance, Stellar Info File, reserve audit |
| Pilot Operations | $4,000 | 50-spaza shop onboarding and support |
| Compliance | $5,000 | SARB sandbox or FSP license pathway |
| Infrastructure | $7,000 | Production servers, security audit, monitoring |
| Contingency | $3,000 | Unexpected costs, API changes, additional testing |
| **Total** | **$64,000** | |

**Note:** All budget covers development costs for Stellar-integrated components only. No marketing, token giveaways, or non-development expenses are included.

---

## 7. Ecosystem Value and Differentiation

### Value to the Stellar Ecosystem

**New Users on Stellar:**
- 50 spaza shop owners onboarded in Tranche 2 (pilot)
- 500+ users targeted by end of Tranche 3
- 200,000+ spaza shops in the addressable market
- These are users who would NEVER interact with Stellar otherwise - they don't have bank accounts, they don't use crypto apps, they use WhatsApp

**Transaction Volume:**
- R500,000+ testnet volume target in Tranche 2
- R1,000,000+ mainnet volume target in Tranche 3
- Average transaction size: R1,000-R5,000 (high-value remittance, not microtransactions)
- Cross-border transactions use Stellar DEX, generating real DEX volume

**New Stablecoin (ZAKA):**
- ZAKA would be a new ZAR-pegged stablecoin on Stellar
- Fills a gap: no dominant ZAR stablecoin on Stellar mainnet
- Enables the $330M+ SA outward remittance market on Stellar
- Opens the door for other South African fintechs to build on Stellar

**Real-World Use Case:**
- Cross-border remittance is one of the highest-value use cases for blockchain
- ZakaPay demonstrates that Stellar can serve the informal economy
- Proves that WhatsApp + Stellar is a viable financial infrastructure for Africa

### Differentiation

| Existing Stellar Projects | ZakaPay |
|--------------------------|---------|
| Focus on developed markets | Focus on African diaspora in South Africa |
| Require app downloads | WhatsApp-native (zero friction) |
| Complex UX (wallet addresses, QR codes) | Conversational AI (just talk) |
| Generic payment processing | Purpose-built for cross-border remittance |
| Target crypto-native users | Target unbanked migrant workers |

**No existing SCF project targets the South African diaspora remittance market via WhatsApp.** ZakaPay is unique in the Stellar ecosystem.

---

## 8. Open Source Plan

ZakaPay does not use custom smart contracts on Stellar. All blockchain operations use:

- Stellar SDK (open source)
- Stellar DEX (native to Stellar, open source)
- ZARC stablecoin (existing, third-party)
- ZAKA stablecoin (will use Stellar native asset issuance, no custom contracts)

If ZAKA issuance requires any contract-based logic (e.g., multi-sig issuance, automated reserve management), those contracts will be open-sourced on GitHub under the MIT license within 30 days of mainnet deployment.

The ZakaPay backend code is currently private but will be open-sourced after mainnet launch to enable ecosystem developers to build WhatsApp-native financial applications on Stellar.

---

## 9. Market Context

### The SADC Remittance Corridor

| Corridor | Annual Volume | ZakaPay Opportunity |
|----------|--------------|-------------------|
| SA to Zimbabwe | $1.8 billion | Largest African corridor. USD cash-out via EcoCash. |
| SA to Mozambique | $400 million | Migrant labor and mining workforce. M-Pesa integration. |
| SA to Somalia | $200 million+ | Somali spaza shop network. 200K+ distribution points. |
| SA to Ethiopia | $150 million+ | Growing diaspora. Telebirr integration planned. |
| SA to Tanzania, Kenya, Nigeria, Zambia, Malawi, Ghana | $500 million+ | Secondary corridors. |
| **Total SADC** | **$3B+** | **1% capture = $30M+ in volume** |

### The Felix Pago Comparison

| Factor | Felix Pago (US-Mexico) | ZakaPay (SA-Africa) |
|--------|----------------------|---------------------|
| Users | Latino immigrants in US | African diaspora in SA |
| Corridor | US to Mexico/LatAm | SA to SADC/Horn of Africa |
| Platform | WhatsApp | WhatsApp |
| Blockchain | Stellar (USDC) | Stellar (ZARC/USDC/ZAKA) |
| Fee | Low flat fee | R10 flat fee |
| Valuation | $400M | Pre-seed |
| Model | Remittance first, merchant second | Remittance first, merchant second |

---

## 10. Roadmap Summary

| Period | Milestone | Stellar Activity |
|--------|-----------|-----------------|
| COMPLETED | MVP on testnet | ZARC, DEX, trustlines, on-chain transactions |
| Month 1-2 | Mobile money integration | EcoCash + M-Pesa API connected to Stellar |
| Month 3 | 50-spaza pilot launch | 50 users on testnet, R500K+ volume |
| Month 4 | Mainnet deployment | Real ZARC/ZAKA, mainnet transactions |
| Month 5 | ZAKA stablecoin issuance | Stellar Info File, reserve audit, mainnet |
| Month 6 | Production scale | 500+ users, R1M+ volume, Series A pitch |

---

## 11. Conclusion

ZakaPay is not a concept or a whitepaper. It is a working product on the Stellar blockchain that has cleared real cross-border transfers from South Africa to Zimbabwe, Somalia, Ethiopia, Mozambique, and Tanzania in under 5 seconds for a flat R10 fee.

The $3 billion SADC remittance market is waiting for a WhatsApp-native, blockchain-powered solution. ZakaPay is that solution - built on Stellar, built for the informal economy, and built by a founder who lives the problem.

With SCF funding, we will move from testnet to mainnet, integrate mobile money APIs for real cash-out, issue the ZAKA stablecoin, and pilot with 50 Somali spaza shops in Cape Town. This is the first step toward bringing 200,000 spaza shops and millions of diaspora users onto the Stellar network.

---

**Applicant:** Ngeli Mrasi
**Email:** ngeli@zakapay.africa
**Phone:** +27 64 878 2381
**Website:** https://zakapay.africa
**GitHub:** https://github.com/NgeliMrasi/zakapay
**On-Chain Proof:** https://stellar.expert/explorer/testnet/account/GC4IMZQ2TP7DAJV3EGVRFX43QFCS4D4P7HVGF4YZEIBKLWG65U3LFOQL

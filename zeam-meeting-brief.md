# ZEAM MEETING BRIEF
## Tuesday, May 19th, 2026 — 11:00 AM (Teams)
## Prepared by: Ngeli Mrasi, Founder of ZakaPay Africa Technologies

---

## ATTENDEES

| Name | Role | Company |
|------|------|---------|
| Tricia Harraway | Product Lead | Zeam Ltd |
| Morné Augustyn | VP of Ecosystems | Zeam Ltd |
| Ngeli Mrasi | Founder and CEO | ZakaPay Africa Technologies |

---

## WHAT ZEAM DOES

Zeam is a Stellar-native financial ecosystem operating as both:
- **Consumer platform:** Zeam wallet (app) for cross-border transfers, payments, airtime
- **B2B infrastructure (Zeam Connect):** Single API for fintechs to move money between fiat and stablecoins across 55+ countries
- **Blockchain settlement:** Uses Stellar, Ethereum, and Solana for on-chain settlement
- **Compliance engine:** KYB, Travel Rule, Sanctions screening as "Step 0" orchestration

Key products:
- Zeam Wallet (iOS/Android)
- Zeam Business Account
- Zeam Connect API
- Stablecoins: ZAR, BTCZ, EURZ, Gold wallets

---

## WHY THEY REACHED OUT

Tricia's exact words: "I really like the look of the service you are offering, very cool! I definitely think we need to see how we can work together."

Three reasons this makes sense:

1. **Same blockchain (Stellar):** Zeam is Stellar-native. We cleared 9 transactions on Stellar testnet. They see a developer building on their network.

2. **WhatsApp = their missing piece:** Zeam has an app. But the 18 million unbanked and migrant workers in South Africa don't want to download another app. ZakaPay IS the WhatsApp layer they can't build.

3. **Township distribution:** Zeam wants to reach spaza shops and informal traders. ZakaPay's 200,000 spaza shop acquisition strategy is exactly what they need.

---

## THE PITCH (2 minutes)

"ZakaPay is a WhatsApp-native cross-border remittance platform built on the Stellar blockchain. We let migrant workers and diaspora communities in South Africa send money home to 10 African countries via WhatsApp for a flat R10 fee, with 5-second settlement.

We've built the full stack: KYC via WhatsApp selfie, on-chain deposits and withdrawals, cross-border transfers to Zimbabwe, Somalia, Ethiopia, Mozambique, and Tanzania — all verified on the Stellar testnet with 9 on-chain transactions.

The entire prototype was built on a smartphone using Termux in 3 weeks.

What makes us different from an app-based solution is zero friction. No app download. No data bundle. No bank account. Just WhatsApp — the app everyone already has.

Our acquisition strategy targets 200,000 Somali-owned spaza shops as distribution points. One owner saves R1,500/month vs Western Union, tells ten cousins, and the savings go viral through the network.

We see a strong strategic fit with Zeam. You provide the infrastructure — the rails, the compliance, the stablecoin ecosystem. We provide the last mile — WhatsApp, spaza shops, township distribution. Together, we complete the stack."

---

## THREE PARTNERSHIP OPTIONS

Present these as options, not demands. Let Tricia and Morne choose.

### Option 1: Zeam Connect API Integration (Light Partnership)

**What it means:**
ZakaPay integrates Zeam Connect API as our backend rails for fiat-to-stablecoin conversion and cross-border settlement.

**What Zeam gets:**
- Transaction volume flowing through their API
- A WhatsApp-native use case to showcase
- Zero development cost for them

**What ZakaPay gets:**
- Production-grade infrastructure without building from scratch
- Access to 55+ country corridors via Zeam Connect
- Compliance engine (KYB, Travel Rule) handled by Zeam

**Technical:**
- ZakaPay backend calls Zeam Connect API for FX conversion and settlement
- Stellar transactions route through Zeam's infrastructure
- ZakaPay handles WhatsApp UX, KYC, and user management

**Budget:** ZakaPay pays Zeam API fees per transaction

---

### Option 2: Embedded WhatsApp Integration (Deep Partnership)

**What it means:**
Zeam embeds ZakaPay's WhatsApp interface into their ecosystem. Zeam users can send money via WhatsApp without downloading the Zeam app.

**What Zeam gets:**
- WhatsApp distribution channel (their biggest gap)
- Access to 200,000 spaza shops for cash-in/cash-out
- Township market penetration they can't achieve with an app
- A compelling story for investors and regulators

**What ZakaPay gets:**
- Zeam's user base and brand credibility
- Zeam's compliance and licensing
- Revenue share on transactions

**Technical:**
- ZakaPay WhatsApp bot connects to Zeam's backend
- Zeam handles settlement, compliance, and reserves
- ZakaPay handles UX, AI, and last-mile distribution

**Revenue split:** To be negotiated

---

### Option 3: Acquisition / Studio Partnership (Strategic)

**What it means:**
Zeam brings ZakaPay into their ecosystem as a product or subsidiary. ZakaPay becomes Zeam's WhatsApp-native remittance product.

**What Zeam gets:**
- A working WhatsApp-native remittance product (built, tested, on-chain)
- A founder who understands the township market from lived experience
- First-mover advantage in WhatsApp-native African remittance

**What ZakaPay gets:**
- Resources to scale (funding, team, infrastructure)
- Zeam's compliance and licensing
- Access to 55+ country corridors

**Technical:**
- ZakaPay integrates fully into Zeam's infrastructure
- Ngeli joins Zeam as Head of WhatsApp Payments or similar
- ZakaPay brand maintained or merged

**Terms:** To be discussed

---

## OBJECTION HANDLING

### "Why not just build WhatsApp integration ourselves?"

You could. But ZakaPay has:
- Working product (9 on-chain transactions)
- 3 weeks of WhatsApp UX testing and iteration
- Conversational AI tuned for financial commands
- The founder who understands the township user
- First-mover advantage

Building from scratch takes 3-6 months. ZakaPay is ready now.

### "The WhatsApp API has limitations for financial services."

We've already solved this:
- Twilio WhatsApp Business API for message handling
- Structured flows for KYC, deposits, transfers
- Error handling for every edge case
- Admin dashboard for compliance

### "How do you handle compliance?"

Currently:
- WhatsApp-native KYC (selfie + ID photo)
- Admin dashboard for manual review
- FICA-ready pipeline

With Zeam:
- Zeam's KYB/Sanctions/Travel Rule engine handles compliance
- ZakaPay handles user-facing KYC collection
- Combined stack is fully compliant

### "What about the SARB and regulation?"

Two pathways:
1. SARB Innovation Hub sandbox (free, 12-month testing period, up to 100 users)
2. FSP license (3-6 months, R50K-R150K cost)

With Zeam's existing compliance infrastructure, the regulatory pathway becomes much simpler.

### "You're a solo founder. Can you scale?"

- Built a full product in 3 weeks on a smartphone
- Currently applying to Antler, Founders Factory, and SCF ($64K)
- AI co-founders enable 24/7 development velocity
- With Zeam's resources, scaling becomes trivial

---

## KEY NUMBERS TO HAVE READY

| Metric | Number | Source |
|--------|--------|--------|
| SA outward remittance | $330M+ | SARB/World Bank |
| SA to Zimbabwe corridor | $1.8B | Largest in Africa |
| SADC total remittance | $3B+ | World Bank RPW |
| FNB eWallet users | 8.2 million | FNB/Daily Investor |
| FNB eWallet volume | R43 billion | FNB/Daily Investor |
| Spaza shops in SA | 200,000+ | SARS |
| Somali-owned spaza shops | ~98% | Industry estimate |
| ZakaPay fee | R10 flat | Our pricing |
| Western Union fee (R2,000 transfer) | R200+ | 10% cost |
| Recipient gets more with ZakaPay | USD 9.66 | Calculated |
| Annual saving per sender | R22,800 | Calculated |
| Felix Pago valuation | $400M | Public |
| On-chain transactions | 9 verified | Stellar testnet |
| Countries supported | 10 African | Built |
| Settlement time | 5 seconds | Stellar |

---

## WHAT TO BRING/SHOW

1. **Live WhatsApp demo** (have the bot ready on your phone)
2. **Stellar Explorer** (show 9 on-chain transactions)
3. **Landing page** (zakapay.africa on your phone)
4. **Comparison page** (zakapay.onrender.com/compare)
5. **One-pager** (print or PDF with key numbers)

---

## MEETING STRUCTURE (45 minutes)

| Time | Agenda | Who |
|------|--------|-----|
| 0:00-5:00 | Introductions | Everyone |
| 5:00-10:00 | Zeam overview (let THEM talk) | Tricia/Morne |
| 10:00-18:00 | ZakaPay pitch + live demo | Ngeli |
| 18:00-25:00 | Partnership options | Ngeli |
| 25:00-35:00 | Discussion and questions | Everyone |
| 35:00-40:00 | Next steps | Everyone |
| 40:00-45:00 | Close | Everyone |

**KEY RULE: Let them talk first.** Ask Tricia and Morne about Zeam's ecosystem before you pitch. The more they talk, the more you understand how to position ZakaPay.

**Questions to ask THEM:**

1. "What corridors are you most focused on right now?"
2. "What's your biggest challenge in reaching township users?"
3. "How are you currently handling last-mile distribution?"
4. "What does your ideal partnership look like?"
5. "Are you exploring WhatsApp as a channel?"

---

## FOLLOW-UP EMAIL (send within 2 hours of meeting)

Subject: ZakaPay x Zeam — Partnership Discussion Follow-Up

Hi Tricia and Morne,

Thank you for the conversation today. I really enjoyed learning about Zeam's ecosystem and vision.

As discussed, here are the key links:
- Landing page: https://zakapay.africa
- On-chain proof: [Stellar Explorer link]
- GitHub: https://github.com/NgeliMrasi/zakapay

I'm excited about the potential synergy between Zeam's infrastructure and ZakaPay's WhatsApp-native last mile. I believe together we can reach the millions of migrant workers and diaspora communities who need affordable cross-border payments.

I'll follow up with [specific next step discussed] by [date].

Looking forward to the next conversation.

Warm regards,
Ngeli Mrasi
Founder, ZakaPay Africa Technologies
ngeli@zakapay.africa
+27 64 878 2381

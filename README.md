# ZakaPay

**Banking without a bank.**

ZakaPay is an AI-powered WhatsApp payment platform built on the Stellar blockchain. It enables unbanked South Africans to send, receive, and store money using only WhatsApp.

## What It Does

- Register a wallet via WhatsApp
- Check live balance from Stellar blockchain
- Send money peer-to-peer via WhatsApp
- All on a phone. No cloud. No bank.

## Architecture

WhatsApp -> Twilio/360dialog -> Cloudflare -> Flask API -> Stellar Blockchain

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/ping | GET | Health check |
| /api/v1/register | POST | Create wallet |
| /api/v1/pin/verify | POST | Verify PIN |
| /api/v1/wallet/balance | GET | Check balance |
| /api/v1/transfer/send | POST | Send XLM |
| /api/v1/contacts/list | GET | List users |
| /api/v1/webhook/whatsapp | POST | WhatsApp webhook |
| /webhook | POST | Twilio webhook |

## Live Transactions on Stellar Testnet

| Transaction | Hash |
|-------------|------|
| Friendbot funding | b5a3e31cc0ca0edff5b4e71412461d824ffac9f32a63f2063ea664c59d181f64 |
| First signed transaction | 5a2de62ab69d9fbda6957df02a00f1782641a5f46ad1a9fe8e71244a59667438 |
| P2P: Thabo to Naledi | 47ced31b6cc26a3195e82078100964940ffa9c87b24dc390278fdb26e13d5306 |
| WhatsApp payment | d1a37ac16de8db66 |

Verify at: https://stellar.expert/explorer/testnet/

## The Team

- **Ngeli Mrasi** — Founder and CEO
- **MiMo (Xiaomi AI)** — Technical Co-Founder
- **Gemini (Google AI)** — Strategy and Research

## Target Market

18 million unbanked South Africans. 200,000+ spaza shops.

## License

Proprietary. ZakaPay Africa 2026.

# The Sloth Shoebox

> **Local-first expense tracking from the payment artifacts you already have.**

> No cloud. No accounts. No subscriptions. No SMS permissions. Just a folder, an open-weight vision model, and a ledger that builds itself.

---

## Table of Contents

- [1. What Is The Sloth Shoebox?](#1-what-is-the-sloth-shoebox)
- [2. The Problem](#2-the-problem)
- [3. The Solution](#3-the-solution)
- [4. Feature Set](#4-feature-set)
- [5. System Architecture](#5-system-architecture)
- [6. Technology Stack](#6-technology-stack)
- [7. Data Model](#7-data-model)
- [8. Privacy and Security Model](#8-privacy-and-security-model)
- [9. Comparison With Existing Tools](#9-comparison-with-existing-tools)
- [10. Why Open Source and Open Weights Matter Here](#10-why-open-source-and-open-weights-matter-here)
- [11. Who Is This For](#11-who-is-this-for)
- [12. Getting Started](#12-getting-started)
- [13. Repository Layout](#13-repository-layout)
- [14. Roadmap](#14-roadmap)
- [15. FAQ](#15-faq)
- [16. Contributing and License](#16-contributing-and-license)
- [Appendix A. Market Research Notes](#appendix-a-market-research-notes)

---

## 1. What Is The Sloth Shoebox?

The Sloth Shoebox is a fully local, open-source application that converts the payment artifacts people already produce — receipt photographs, UPI transaction screenshots, PDF bills, bank statement exports — into a structured, categorized, exportable expense ledger. The user performs exactly one action: dropping files into a folder. Everything else happens automatically, on their own machine, using open-weight vision-language models served locally through Ollama.

The name comes from the shoebox of crumpled receipts that people traditionally shove into a drawer and dread at tax time. The Sloth Shoebox does what a patient sloth would do: it takes that chaotic pile, works through it slowly and reliably, and hands back a clean ledger without ever asking anyone to type, upload, or sign up for anything.

The project exists for a specific audience that consumer fintech consistently ignores: students, roommates splitting bills, freelancers, and anyone managing a tight budget — people who cannot justify a monthly subscription to understand where their money goes, and who should not have to hand their financial life to a cloud service in order to find out.

### Design Principles

1. **Zero new behavior.** The user already screenshots UPI payments and photographs receipts. The app consumes those exact artifacts; it never asks for a new habit.
2. **Local-only inference.** Every byte of every image and every parsed field stays on the user's device. There is no server, no API key, and no telemetry.
3. **Free forever.** Local inference has zero marginal cost per document, so the app can be genuinely free without a freemium trap.
4. **Schema-strict parsing.** Model output is validated against a fixed schema before it touches the database. Bad parses are quarantined for review, never silently stored.

---

## 2. The Problem

### 2.1 Expense tracking today is broken for the people who need it most

Every mainstream solution to personal expense tracking fails one of three ways: it reads data it should never touch, it makes the human do the work, or it charges a recurring fee that its most vulnerable audience cannot afford. The verified state of the market as of October 2026 makes this pattern unusually clear.

| Solution | Model | Where It Fails |
|---|---|---|
| Splitwise | Freemium, Pro at USD 4.99/month | Free tier caps expense entry at roughly 3 to 4 per day and shows ads; receipt scanning is a Pro-only feature |
| Expensify | Freemium, business-first | 25 free receipt scans per month, then paid; designed for corporate reimbursement, not canteen budgets |
| Walnut (India's most-used tracker) | Dead | Read the user's SMS inbox — including OTP codes — and shut down after trust collapsed |
| Cashiro (open source, F-Droid) | Free and offline | Parses bank SMS with regex only; cannot read receipt photos, screenshots, or PDFs; no fuzzy categorization |
| Cashew, Goodbudget, TrackMyRupee | Free/manual or subscription | The human is the parser; every expense must be typed by hand |

### 2.2 The data already exists — it is just buried

A typical student's spending history is already recorded, in fragments, across three places: UPI payment screenshots saved in their phone gallery, e-commerce order and refund confirmations sitting in email as PDFs or images, and photographs of paper receipts shared in family or roommate group chats. None of this was created for bookkeeping, yet together it forms a nearly complete ledger. No existing product parses these artifacts, and no product parses them locally.

### 2.3 The privacy trap that killed the last generation of automation

The previous wave of automatic expense trackers in India (Walnut and similar) worked by requesting permission to read every incoming SMS. That permission level includes bank balances, transaction alerts, and one-time passwords — the single most sensitive inbox on a phone. Users reasonably rejected this trade, the category collapsed, and the apps that survived retreated to manual entry. The lesson is direct: automation that requires surveilling the user is not automation people want. The Sloth Shoebox sidesteps the trap entirely by needing no permissions at all — only the files the user chose to keep.

---

## 3. The Solution

### 3.1 Core concept: artifact mining

The Sloth Shoebox treats existing payment artifacts as raw data and applies a locally hosted, open-weight vision-language model to extract structured transactions from them. A folder watcher ingests images and PDFs, a deduplication pass discards repeats, the model parses each artifact into a strict JSON schema, and validated records land in a local SQLite ledger with automatic category assignment and merchant normalization. Exports to CSV and XLSX, a monthly digest, and a plain-language query interface complete the loop.

### 3.2 The UPI screenshot goldmine

In India, every meaningful digital payment generates a confirmation screen that people habitually screenshot — as proof of payment, to share in group chats, or simply by reflex. Galleries across the country contain years of complete, timestamped, merchant-signed spending records that no tool has ever mined. Pointing a local vision model at that pile is the project's hero feature: the user's financial history is already photographed; it only needs reading. Because the source is a screenshot the user saved voluntarily, the app never needs SMS access, bank credentials, or any integration whatsoever — the exact failure mode that killed the previous generation of trackers is structurally impossible here.

### 3.3 What the pipeline guarantees

- **Deduplication before inference.** Perceptual hashing catches the same screenshot saved twice, and reference-number matching merges a receipt photo with the UPI screenshot of the same payment.
- **Schema-strict output.** The model must return valid JSON against a fixed schema; malformed parses are re-asked once and then quarantined, never guessed into the ledger.
- **Graceful degradation.** Confusing thermal receipts fall back to offline OCR (Tesseract); low-power machines automatically select smaller models; everything still works with the network cable unplugged.
- **Human review where it matters.** Low-confidence parses are flagged for a one-tap confirm, rather than silently committed.

---

## 4. Feature Set

### 4.1 Tier 0 — MVP (hackathon scope)

| Feature | Description |
|---|---|
| Folder ingestion | Watch a folder, accept drag-and-drop, or pick from a gallery |
| Duplicate rejection | Perceptual hash dedupe at ingest; reference-number merge across artifact types |
| Local VLM parsing | Ollama-hosted open-weight vision model extracts vendor, amount, currency, datetime, category, payment reference, status, and document type |
| Failed-payment filtering | Detects failed or reversed UPI screenshots and skips them |
| Auto-categorization | Rule plus model hybrid: food, travel, rent, books, subscriptions, utilities, with fuzzy merchant normalization |
| SQLite ledger | Single-file local database; fully inspectable |
| Exports | CSV and XLSX output, one click, no account |
| Monthly digest | Plain summary of totals, top merchants, and category deltas versus the trailing three-month average |
| Offline query | Natural-language questions answered locally over the ledger |

### 4.2 Tier 1 — The student stack

| Feature | Description |
|---|---|
| Roommate split engine | Snap a group-dinner receipt; the model itemizes line-by-line; tap to assign participants; settlement amounts computed with simplified debts |
| Refund tracker | Flags e-commerce orders with no matching refund after a configurable window and drafts a follow-up message |
| Subscription leak detector | Parses local PDF bank and card statements; detects recurring charges; reports subscriptions that show no matching usage |
| Tax-time export | Per-category CSV with GST or VAT amounts extracted from invoices and probable-deductible flags for side income |
| Warranty linking | Attach a parsed purchase receipt to a product entry so the bill is findable in two years |
| Bank CSV reconciliation | Match parsed receipts against exported statement lines to catch double charges |

### 4.3 Tier 2 — Long-term roadmap

- Fully offline phone client (PWA) with LAN-only sync between phone and desktop.
- Receipt-to-warranty lifecycle reminders.
- Multi-currency handling with offline exchange-rate snapshots for travel.
- Community-maintained merchant and category packs.
- Optional fine-tuning of the parsing model on anonymized, user-consented receipt layouts.

---

## 5. System Architecture

### 5.1 Pipeline overview
```

Inbox folder (gallery picker / Downloads watcher / drag-and-drop)

|

v

[1] Ingest + perceptual-hash dedupe

|

v

[2] Local VLM via Ollama (open weights, no API key)

Prompt -> strict JSON: vendor, amount, currency, datetime,

category, payment_ref, status, doc_type, gst_amount

|

v

[3] Schema validation (Pydantic)

-- malformed -> single re-ask -> quarantine on failure

-- low confidence -> user review queue

|

v

[4] SQLite ledger

+ fuzzy merchant normalization

+ cross-artifact transaction merge

|

v

[5] Outputs: CSV / XLSX export, monthly digest,

offline natural-language queries, split sheets

```

### 5.2 Component responsibilities

| Component | Responsibility | Failure Handling |
|---|---|---|
| Ingest watcher | Detect new files, classify type (image, PDF, screenshot) | Unreadable files quarantined with reason |
| Deduper | Perceptual hash on images, reference-number match across records | Duplicate logs kept for audit |
| Parser (VLM) | Extract structured fields from artifacts | One re-ask on malformed JSON, then quarantine |
| Validator | Enforce schema and sanity checks (amount range, date plausibility) | Low-confidence rows go to review queue |
| Ledger | SQLite storage, category assignment, merchant normalization | Single transaction per batch; crash-safe |
| Exporter | CSV / XLSX generation, digest rendering | Fully deterministic, no model involvement |

### 5.3 Degradation ladder

1. Primary: open-weight VLM through Ollama (Qwen3.8-Vision or Gemma 4 family).
2. Assist: Tesseract OCR fusion when the VLM reports low confidence on thermal or handwritten receipts.
3. Fallback: smaller vision models (Moondream, MiniCPM-V) on low-RAM machines.
4. Floor: manual review queue — the app still functions with zero successful parses.

---

## 6. Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Model runtime | Ollama | One-command local serving with an OpenAI-compatible API; no key management |
| Vision model (16 GB+) | Qwen3.8-Vision 27B (4-bit, 16 to 19 GB) | Strong document and screenshot parsing; Apache-licensed family |
| Vision model (8 to 12 GB) | Gemma 4 12B | Laptop-friendly multimodal parsing |
| Vision model (low-end) | Moondream / MiniCPM-V | Usable on modest hardware |
| Text tasks | Phi-4-mini or Qwen3 small | Digests, categorization refinement, draft messages; MIT/Apache licensed |
| OCR assist | Tesseract | Offline, deterministic fallback |
| Backend | Python, FastAPI | Small surface, easy local API |
| Validation | Pydantic | Strict schema enforcement at the parse boundary |
| Storage | SQLite | Single file, inspectable, zero configuration |
| Frontend | Minimal web UI (local only) | Folder input, ledger table, charts, export button |

### Model selection by hardware

| Machine | Recommended Model | Notes |
|---|---|---|
| 8 GB RAM laptop | Moondream or MiniCPM-V | Slower but fully functional |
| 12 to 16 GB RAM | Gemma 4 12B | Best balance for most students |
| 16 to 19 GB+ | Qwen3.8-Vision 27B (4-bit) | Highest parse accuracy |
| Apple Silicon | MLX builds via LM Studio alternative or Ollama | Native acceleration |

---

## 7. Data Model

### 7.1 Parsed transaction schema (model output contract)
```json

{

"doc_type": "upi_screenshot | receipt_photo | pdf_bill | statement_line",

"vendor_raw": "Swiggy",

"vendor_normalized": "swiggy",

"amount": 342.50,

"currency": "INR",

"datetime_local": "2026-10-19T21:14:05",

"category": "food",

"payment_ref": "UPI/519812345678/Payment/...",

"payment_app": "gpay",

"status": "success | failed | reversed",

"gst_amount": 17.13,

"confidence": 0.93,

"source_file": "IMG_20261019_21140501.jpg",

"content_hash": "phash:9f2a..."

}

```

### 7.2 SQLite core tables
```sql

CREATE TABLE transactions (

id INTEGER PRIMARY KEY,

vendor_normalized TEXT NOT NULL,

vendor_raw TEXT,

amount REAL NOT NULL CHECK (amount > 0),

currency TEXT NOT NULL DEFAULT 'INR',

datetime_local TEXT NOT NULL,

category TEXT NOT NULL,

payment_ref TEXT UNIQUE,

payment_app TEXT,

doc_type TEXT NOT NULL,

status TEXT NOT NULL DEFAULT 'success',

gst_amount REAL,

confidence REAL,

source_file TEXT,

content_hash TEXT UNIQUE,

review_flag INTEGER DEFAULT 0,

created_at TEXT DEFAULT CURRENT_TIMESTAMP

);

CREATE TABLE splits (

id INTEGER PRIMARY KEY,

transaction_id INTEGER REFERENCES transactions(id),

participant TEXT NOT NULL,

share REAL NOT NULL,

settled INTEGER DEFAULT 0

);

CREATE TABLE quarantined_parses (

id INTEGER PRIMARY KEY,

source_file TEXT,

reason TEXT,

raw_output TEXT,

created_at TEXT DEFAULT CURRENT_TIMESTAMP

);

```

---

## 8. Privacy and Security Model

The privacy argument is not a marketing layer; it is the architecture. The following table is the complete data-flow contract of the application.

| Question | Answer |
|---|---|
| Where do images go? | Nowhere. They are read from disk by a local process and never transmitted. |
| Where does the model run? | On the user's machine via Ollama with open-weight models. |
| Is there an account? | No. |
| Is there telemetry or analytics? | No. |
| What permissions does the phone or laptop app need? | File access to the folders the user selects. Nothing else. |
| What happens on uninstall? | Delete one SQLite file; the ledger is gone. No remote copy exists. |
| What does a network outage change? | Nothing. The app is fully functional offline by design. |

The SMS-permission approach that defined and destroyed the previous generation of automatic trackers is structurally impossible here: the app's only input is files the user chose to save. There is no inbox access, no bank linking, no credential storage, and no network dependency in the parse path.

---

## 9. Comparison With Existing Tools

| Capability | Sloth Shoebox | Splitwise Free | Splitwise Pro | Expensify Free | Cashiro (OSS) | Manual Trackers |
|---|---|---|---|---|---|---|
| Parses receipt photos | Yes | No | Yes | Yes (25/month) | No | No |
| Parses UPI screenshots | Yes | No | No | No | No | No |
| Parses PDF bills | Yes | No | No | Limited | PDF statements only | No |
| Daily entry limit | None | 3 to 4 | None | Scan cap | None | None (by typing) |
| SMS or bank access | None | None | None | Bank link | SMS access | None |
| Cloud dependency | None | Yes | Yes | Yes | None | Varies |
| Cost | Free, forever | Free with ads | USD 4.99/month | Freemium | Free | Free or subscription |
| Local inference | Yes (open weights) | No | No | No | No regex-only | No |

Verified against public pricing pages and store listings, September to October 2026. Sources and figures are collected in Appendix A.

---

## 10. Why Open Source and Open Weights Matter Here

**The business model of closed AI is the bug this project deletes.** Every closed competitor pays a per-token API bill, which forces a subscription, which prices out exactly the audience that most needs the tool. Local open-weight inference has zero marginal cost per receipt, so genuine free-forever operation is not charity; it is the rational architecture.

> "A cloud API is not just a cost problem here — it is a contradiction. The entire value proposition is that your financial artifacts never leave your machine. Only open weights make that promise deliverable."

**Openness is the trust repair for a burned market.** The category's biggest failure (SMS-reading trackers) was a trust failure. Users cannot audit a closed binary; they can audit this repository. Every claim in Section 8 is verifiable in source.

**Openness is longevity for data people keep for years.** A ledger is a decade-scale artifact. Warranties, tax records, and spending history outlive apps, companies, and business models. An open format on a local SQLite file survives every shutdown that killed Mint and Walnut, and the model layer is swappable because the weights are open and the schema is public.

**Openness is accessibility.** Students on 20-dollar phones and 8-gigabyte laptops are a first-class supported configuration (via the model degradation ladder), not an afterthought. Closed products target paying seats; this project targets people.

---

## 11. Who Is This For

| Persona | Situation | What They Get |
|---|---|---|
| The student | Pays for everything by UPI, screenshots payments by habit, shares bills in group chats | A complete semester ledger built from their gallery, with zero typing |
| The roommate group | Splits rent, groceries, canteen runs; hits Splitwise's free daily cap | Unlimited splits from one receipt photo, free settlement math, no ads |
| The freelancer | Collects paper and PDF invoices, dreads tax season | GST-aware CSV export with deductible flags, built in one evening from a shoebox folder |
| The privacy-conscious professional | Used and abandoned Walnut-class SMS trackers | Full automation with no permissions, no cloud, no account |
| The budget watcher | Wants monthly digests and subscription leak alerts without a bank-linking app | Statement parsing done locally, alerts generated offline |

---

## 12. Getting Started

> This section describes the planned developer setup for the MVP.

### Prerequisites

- Python 3.11 or later
- [Ollama](https://ollama.com) installed and running
- 8 GB RAM minimum (16 GB recommended for the primary model)

### Install
```bash

# 1. Clone the repository

git clone https://github.com//sloth-shoebox.git

cd sloth-shoebox

# 2. Install dependencies

pip install -r requirements.txt

# 3. Pull the parsing model (choose one by hardware)

ollama pull qwen3.8-vision:27b-q4 # 16 to 19 GB class machines

ollama pull gemma4:12b # 12 to 16 GB class machines

ollama pull moondream # low-end machines

# 4. Run the app

python -m sloth_shoebox

```

### First run

1. Open the local UI (http://localhost:8337 by default).
2. Point the inbox at a folder of screenshots and receipt photos.
3. Watch the ledger fill, review any flagged rows, export CSV when done.

---

## 13. Repository Layout
```

sloth-shoebox/

|-- README.md

|-- LICENSE

|-- requirements.txt

|-- sloth_shoebox/

| |-- __init__.py

| |-- app.py # FastAPI app and local UI routes

| |-- ingest.py # Folder watcher and file classification

| |-- dedupe.py # Perceptual hashing and reference merge

| |-- parser.py # Ollama client and prompt templates

| |-- schema.py # Pydantic models for parse contracts

| |-- ledger.py # SQLite layer and migrations

| |-- categorize.py # Rule + model hybrid categorizer

| |-- merchant.py # Fuzzy merchant normalization

| |-- splits.py # Group settlement engine

| |-- export.py # CSV / XLSX writers

| |-- digest.py # Monthly digest generator

| |-- query.py # Offline natural-language queries

| `-- ocr_fallback.py # Tesseract assist path

|-- prompts/

| `-- parse_transaction.txt # Versioned VLM prompts

|-- migrations/

|-- tests/

| |-- fixtures/ # Sample receipts and screenshots

| `-- test_parse_contract.py

`-- docs/

`-- research.md # Market research notes (Appendix A source)

```

---

## 14. Roadmap

### Phase 1 — MVP (hackathon)

- [x] Concept and market validation
- [ ] Ingest, dedupe, and folder watching
- [ ] VLM parse contract with Pydantic validation
- [ ] SQLite ledger and category assignment
- [ ] CSV / XLSX export and monthly digest
- [ ] Offline natural-language queries

### Phase 2 — Student stack

- [ ] Roommate split engine with settlement math
- [ ] Cross-artifact transaction merging
- [ ] Refund tracker with follow-up drafts
- [ ] Subscription leak detector from PDF statements
- [ ] Warranty linking

### Phase 3 — Moat

- [ ] Offline PWA client with LAN-only sync
- [ ] Bank CSV reconciliation
- [ ] Community merchant packs
- [ ] Optional community fine-tunes for receipt layouts

---

## 15. FAQ

**Does this need an internet connection at all?**

Only once, to download the open-weight model. After that, parsing, categorization, queries, digests, and exports all run with the network fully disabled.

**Is a screenshot parser as accurate as a paid receipt scanner?**

For structured UPI confirmations, local vision models are highly reliable because the source layout is machine-generated. For crumpled thermal receipts, the OCR-assist path and review queue handle the residual ambiguity honestly instead of guessing.

**Why parse screenshots instead of reading SMS like older apps?**

Because SMS access means OTP access. The screenshot approach uses artifacts the user saved voluntarily, needs zero permissions, and cannot leak an inbox even in principle.

**What if I have 500 screenshots from two years?**

Batch it. Inference is local and free, so there is no per-document cost to worry about, and the dedupe pass means re-runs are cheap.

**Can this replace my accounting software?**

It is not trying to. It replaces the shoebox: the painful capture-and-organize step, with clean exports that feed whatever system you already use.

---

## 16. Contributing and License

Contributions are welcome, with two standing rules that protect the project's promise: no code may introduce a network call in the parse path, and no dependency may require an account or API key. Both rules are checkable in review and enforced by a lightweight CI check that fails on new outbound connections.

License: MIT (planned). Model weights remain under their respective licenses (Apache 2.0 / MIT families), which is itself part of the point: permissive open weights are what make a fully local build possible.

---

## Appendix A. Market Research Notes

All figures below were verified from public pricing pages, app store listings, and comparison guides between September and October 2026, and are cited in the challenge post narrative.

| Claim | Source Checked | Verified Figure |
|---|---|---|
| Splitwise free tier daily cap | Splitwise Pro page and three independent 2026 reviews | Commonly reported 3 to 4 expenses per day; ads on free tier |
| Splitwise Pro pricing | App Store listings, 2026 pricing guides | USD 4.99/month or USD 39.99/year; receipt scanning Pro-only |
| Expensify free scan limit | Expensify receipt scanning page, 2026 scanner roundups | 25 scans per month on free tier |
| Walnut (India) shutdown | 2026 alternative-app comparisons | SMS-based tracker shut down; SMS permission widely cited as the trust failure |
| Screenshot organizer market | App Store and Microsoft Store listings, Mac comparison guides (Oct 2026) | Subscription tiers at USD 12.99/month; cloud GPT-4V round-trips; no fully local competitor found |
| Open-weight model landscape | Local-LLM guides and Unsloth GGUF listings (Oct 2026) | Qwen3.8-Vision 27B at 16 to 19 GB (4-bit); Gemma 4 12B multimodal; Moondream and MiniCPM-V for low-end |
| Mint retirement | 2026 budgeting app comparisons | Mint retired; users migrated to paid alternatives |

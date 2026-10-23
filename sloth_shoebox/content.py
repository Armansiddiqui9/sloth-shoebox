"""Page copy and tables for the single-page site.

Kept as plain data so copy changes never touch templates or layout.
"""

from __future__ import annotations

NAV = (
    ("problem", "Problem"),
    ("pipeline", "Pipeline"),
    ("demo", "Demo"),
    ("privacy", "Privacy"),
    ("compare", "Compare"),
    ("docs", "Docs"),
    ("faq", "FAQ"),
)

HERO_PROMISES = (
    "No cloud sync",
    "No SMS permission",
    "No API key",
    "No subscription",
    "No daily cap",
)

HERO_CHAIN = (
    "Drop a folder of screenshots",
    "Dedupe",
    "Parse with a local vision model",
    "Validate against a schema",
    "Commit to SQLite",
    "Export CSV",
)

# What the hero memo shows: the three artifacts and the ledger lines they became.
HERO_MEMO = (
    {"vendor": "Swiggy", "detail": "food, gpay, 19 Oct", "rupees": "285", "paise": "50"},
    {
        "vendor": "Brew & Bytes Cafe",
        "detail": "food, receipt, 12 Oct",
        "rupees": "420",
        "paise": "00",
    },
    {"vendor": "Blinkit", "detail": "groceries, paytm, 18 Oct", "rupees": "648", "paise": "75"},
)

PROBLEM_ROWS = (
    (
        "Splitwise",
        "Freemium, Pro at $4.99 a month",
        "Free tier caps expense entry at about 3 to 4 a day and shows ads. Receipt scanning is Pro-only.",
        "Paywall and caps",
    ),
    (
        "Expensify",
        "Freemium, business-first",
        "25 free receipt scans a month, then paid. Built for corporate reimbursement, not canteen budgets.",
        "Scan cap",
    ),
    (
        "Walnut",
        "Shut down",
        "Read the user’s SMS inbox, OTPs included, and closed after trust collapsed.",
        "Privacy trap",
    ),
    (
        "Cashiro",
        "Free, open source",
        "Parses bank SMS with regex only. Can’t read receipt photos, screenshots or PDFs.",
        "Regex only",
    ),
    (
        "Cashew, Goodbudget, TrackMyRupee",
        "Free or subscription",
        "The human is the parser: every expense is typed by hand.",
        "Manual entry",
    ),
)

PROBLEM_NOTES = (
    (
        "The data already exists",
        "A typical student’s spending history is already recorded, in fragments, in three places: "
        "UPI payment screenshots in the gallery, e-commerce order and refund confirmations in email "
        "as PDFs, and photographs of paper receipts shared in group chats. None of it was made for "
        "bookkeeping, yet together it forms a nearly complete ledger.",
    ),
    (
        "The privacy trap",
        "The last wave of automatic trackers worked by reading every incoming SMS, OTPs and bank "
        "alerts included. Users reasonably rejected that trade, the category collapsed, and the "
        "survivors retreated to manual entry. The Sloth Shoebox sidesteps the trap structurally: its "
        "only input is files the user chose to save.",
    ),
)

PIPELINE_STAGES = (
    (
        "Ingest and dedupe",
        "A folder watcher accepts drag-and-drop, a gallery picker, or a Downloads watcher. "
        "Perceptual hashing rejects the same screenshot saved twice; reference-number matching merges "
        "a receipt photo with the UPI screenshot of the same payment.",
        "Unreadable files are quarantined with a reason.",
    ),
    (
        "Local vision-model parse",
        "An open-weight vision model served through Ollama extracts vendor, amount, currency, "
        "datetime, category, payment reference, status and document type. No API key. No network "
        "call in the parse path.",
        "One re-ask on malformed JSON, then quarantine.",
    ),
    (
        "Schema validation",
        "Model output is validated against a fixed Pydantic schema before it touches the database, "
        "with sanity checks on amount range and date plausibility. Low-confidence rows go to a review "
        "queue and are never silently stored.",
        "Bad parses are quarantined, not guessed.",
    ),
    (
        "SQLite ledger",
        "Validated records land in a single-file local database with automatic category assignment "
        "and fuzzy merchant normalisation. Cross-artifact merging ties the receipt photo to the UPI "
        "screenshot of the same payment.",
        "One transaction per batch, crash-safe.",
    ),
    (
        "Outputs",
        "CSV export in one click. A monthly digest reports totals, top merchants and category deltas "
        "against the trailing three-month average. Offline natural-language queries answer questions "
        "over the ledger locally.",
        "Nothing to misread: no model is involved.",
    ),
)

DEGRADATION = (
    (
        "Primary",
        "Qwen3.8-Vision 27B, 4-bit",
        "Machines with 16 to 19 GB+ of RAM",
        "Strongest document and screenshot parsing. Apache-licensed family.",
    ),
    (
        "Assist",
        "Tesseract OCR fusion",
        "Thermal and handwritten receipts",
        "Offline, deterministic fallback when the vision model reports low confidence.",
    ),
    (
        "Floor",
        "Moondream or MiniCPM-V",
        "8 GB RAM laptops",
        "Slower but fully functional. The app still works at zero successful parses.",
    ),
)

PRIVACY_CONTRACT = (
    (
        "Where do images go?",
        "Nowhere. They are read from disk by a local process and never transmitted.",
    ),
    (
        "Where does the model run?",
        "On the user’s machine through Ollama, with open-weight models. No API key, no remote inference.",
    ),
    ("Is there an account?", "No. No email, no password, no profile."),
    (
        "Is there telemetry or analytics?",
        "No. The repo is auditable and the parse path is verifiably network-free.",
    ),
    (
        "What permissions does the app need?",
        "File access to the folders the user selects. No SMS, no contacts, no clipboard, no notifications.",
    ),
    (
        "What happens on uninstall?",
        "Delete one SQLite file and the ledger is gone. No remote copy exists.",
    ),
    (
        "What does a network outage change?",
        "Nothing. The app is fully functional offline by design.",
    ),
)

PRIVACY_GUARANTEE = (
    "The SMS-permission approach that defined and destroyed the previous generation of automatic "
    "trackers is structurally impossible here. The app’s only input is files the user chose to "
    "save. There is no inbox access, no bank linking, no credential storage, and no network "
    "dependency in the parse path."
)

# Every cell is phrased so "yes" is good for the user.
COMPARE_COLUMNS = (
    ("sloth", "Sloth Shoebox"),
    ("split_free", "Splitwise Free"),
    ("split_pro", "Splitwise Pro"),
    ("expensify", "Expensify Free"),
    ("cashiro", "Cashiro (OSS)"),
    ("manual", "Manual trackers"),
)

COMPARE_ROWS = (
    ("Parses receipt photos", "yes", "no", "yes", "limited", "no", "no"),
    ("Parses UPI screenshots", "yes", "no", "no", "no", "no", "no"),
    ("Parses PDF bills", "yes", "no", "no", "limited", "limited", "no"),
    ("No daily entry limit", "yes", "limited", "yes", "limited", "yes", "yes"),
    ("Works without SMS or bank access", "yes", "yes", "yes", "no", "no", "yes"),
    ("No cloud dependency", "yes", "no", "no", "no", "yes", "limited"),
    ("Free forever", "yes", "no", "no", "no", "yes", "limited"),
    ("Local inference with open weights", "yes", "no", "no", "no", "no", "no"),
)

COMPARE_MARKS = {"yes": "Yes", "no": "No", "limited": "Limited"}

PERSONAS = (
    (
        "The student",
        "Pays for everything by UPI, screenshots payments by habit, shares bills in group chats.",
        "A complete semester ledger built from their gallery, with zero typing.",
        "IMG_20261019_21140501.jpg",
    ),
    (
        "The roommate group",
        "Splits rent, groceries and canteen runs, and hits Splitwise’s free daily cap.",
        "Unlimited splits from one receipt photo, free settlement math, no ads.",
        "receipt_group_dinner.jpg",
    ),
    (
        "The freelancer",
        "Collects paper and PDF invoices and dreads tax season.",
        "GST-aware CSV export with deductible flags, built in one evening from a shoebox folder.",
        "invoice_client_07.pdf",
    ),
    (
        "The privacy-conscious professional",
        "Used and abandoned Walnut-class SMS trackers.",
        "Full automation with no permissions, no cloud, no account.",
        "statement_oct.pdf",
    ),
    (
        "The budget watcher",
        "Wants monthly digests and subscription-leak alerts without a bank-linking app.",
        "Statement parsing done locally, alerts generated offline.",
        "card_statement.csv",
    ),
)

ROADMAP = (
    (
        "Phase 1",
        "MVP (hackathon)",
        "In progress",
        (
            ("Concept and market validation", True),
            ("Ingest, dedupe and folder watching", False),
            ("Vision-model parse contract with Pydantic validation", False),
            ("SQLite ledger and category assignment", False),
            ("CSV and XLSX export and monthly digest", False),
            ("Offline natural-language queries", False),
        ),
    ),
    (
        "Phase 2",
        "Student stack",
        "Planned",
        (
            ("Roommate split engine with settlement math", False),
            ("Cross-artifact transaction merging", False),
            ("Refund tracker with follow-up drafts", False),
            ("Subscription-leak detector from PDF statements", False),
            ("Warranty linking", False),
        ),
    ),
    (
        "Phase 3",
        "Moat",
        "Planned",
        (
            ("Offline PWA client with LAN-only sync", False),
            ("Bank CSV reconciliation", False),
            ("Community merchant packs", False),
            ("Optional community fine-tunes for receipt layouts", False),
        ),
    ),
)

FAQ = (
    (
        "Does this need an internet connection at all?",
        "Only once, to download the open-weight model. After that, parsing, categorisation, queries, "
        "digests and exports all run with the network fully disabled.",
    ),
    (
        "Is a screenshot parser as accurate as a paid receipt scanner?",
        "For structured UPI confirmations, local vision models are highly reliable because the source "
        "layout is machine-generated. For crumpled thermal receipts, the OCR-assist path and review "
        "queue handle the residual ambiguity honestly instead of guessing.",
    ),
    (
        "Why parse screenshots instead of reading SMS like older apps?",
        "Because SMS access means OTP access. The screenshot approach uses artifacts the user saved "
        "voluntarily, needs zero permissions, and cannot leak an inbox even in principle.",
    ),
    (
        "What if I have 500 screenshots from two years?",
        "Batch it. Inference is local and free, so there is no per-document cost to worry about, and "
        "the dedupe pass means re-runs are cheap.",
    ),
    (
        "Can this replace my accounting software?",
        "It is not trying to. It replaces the shoebox: the painful capture-and-organise step, with "
        "clean exports that feed whatever system you already use.",
    ),
    (
        "What hardware do I need?",
        "8 GB RAM minimum (Moondream or MiniCPM-V). 12 to 16 GB gets you Gemma 4 12B. 16 to 19 GB+ "
        "unlocks Qwen3.8-Vision 27B at 4-bit. Apple Silicon uses MLX builds through LM Studio or "
        "Ollama for native acceleration.",
    ),
    (
        "What if the model misparses a receipt?",
        "Low-confidence parses go to a review queue: they are committed to the ledger but flagged for "
        "a one-tap confirm, never silently stored as fact. Bad parses that fail schema validation are "
        "quarantined, not guessed into the database.",
    ),
)

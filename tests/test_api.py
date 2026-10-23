from __future__ import annotations


def test_health_and_page(client):
    assert client.get("/api/health").json()["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200
    assert "Your phone gallery is already a ledger." in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]


def test_seeded_ledger_counts(client):
    everything = client.get("/api/ledger", params={"status": "all", "limit": 100}).json()
    assert everything["total_count"] == 28
    default = client.get("/api/ledger").json()
    assert default["total_count"] == 26  # failed and reversed are hidden by default
    bad = client.get("/api/ledger", params={"status": "failed,reversed"}).json()
    assert {t["status"] for t in bad["transactions"]} == {"failed", "reversed"}


def test_ledger_filters_and_search(client):
    food = client.get("/api/ledger", params={"category": "food"}).json()
    assert food["transactions"] and all(t["category"] == "food" for t in food["transactions"])
    hits = client.get("/api/ledger", params={"q": "swig"}).json()
    assert hits["total"] >= 3
    assert client.get("/api/ledger", params={"q": "100%"}).json()["total"] == 0  # LIKE is escaped


def test_patch_and_delete(client):
    tx = client.get("/api/ledger").json()["transactions"][0]
    patched = client.patch(
        f"/api/ledger/{tx['id']}", json={"category": "books", "notes": "text", "review_flag": 1}
    ).json()["transaction"]
    assert (patched["category"], patched["notes"], patched["review_flag"]) == ("books", "text", 1)
    cleared = client.patch(f"/api/ledger/{tx['id']}", json={"notes": None}).json()["transaction"]
    assert cleared["notes"] is None
    assert client.patch(f"/api/ledger/{tx['id']}", json={"category": "nope"}).status_code == 422
    assert client.delete(f"/api/ledger/{tx['id']}").json()["ok"] is True
    assert client.get(f"/api/ledger/{tx['id']}").status_code == 404
    assert client.delete(f"/api/ledger/{tx['id']}").status_code == 404


def test_ingest_sample_paths(client):
    ok = client.post("/api/ingest", json={"sample_id": "swiggy"}).json()
    assert ok["artifact"]["stage"] == "committed"
    assert ok["stages"][-1] == "committed"
    assert ok["transaction"]["amount"] == 285.5

    dup = client.post("/api/ingest", json={"sample_id": "swiggy"}).json()
    assert dup["artifact"]["stage"] == "quarantined"
    assert "Duplicate" in dup["quarantined"]["reason"]

    review = client.post("/api/ingest", json={"sample_id": "cafe"}).json()
    assert review["artifact"]["stage"] == "committed"  # 0.88 confidence is above the 0.8 line

    bad = client.post("/api/ingest", json={"sample_id": "failed"}).json()
    assert bad["artifact"]["stage"] == "quarantined"
    assert "category" in bad["quarantined"]["reason"]

    assert client.post("/api/ingest", json={"sample_id": "nope"}).status_code == 404


def test_ingest_upload(client):
    data = b"\x89PNG not really a picture but the stand-in parser never looks"
    first = client.post(
        "/api/ingest/upload", files={"file": ("shot.png", data, "image/png")}
    ).json()
    assert first["artifact"]["stage"] in {"committed", "review"}
    again = client.post(
        "/api/ingest/upload", files={"file": ("shot.png", data, "image/png")}
    ).json()
    assert again["artifact"]["stage"] == "quarantined"
    empty = client.post("/api/ingest/upload", files={"file": ("e.png", b"", "image/png")})
    assert empty.status_code == 400


def test_upload_of_a_shipped_sample_uses_its_parse(client):
    from sloth_shoebox.samples import SAMPLES_DIR

    blob = (SAMPLES_DIR / "upi-blinkit.webp").read_bytes()
    result = client.post(
        "/api/ingest/upload", files={"file": ("whatever.webp", blob, "image/webp")}
    ).json()
    assert result["transaction"]["vendor_normalized"] == "blinkit"


def test_inbox_list_and_delete(client):
    client.post("/api/ingest", json={"sample_id": "failed"})
    artifacts = client.get("/api/inbox").json()["artifacts"]
    assert artifacts[0]["file_name"] == "upi-failed.png"
    assert client.delete(f"/api/inbox/{artifacts[0]['id']}").json()["ok"] is True
    assert client.delete(f"/api/inbox/{artifacts[0]['id']}").status_code == 404


def test_digest_endpoint(client):
    d = client.get("/api/digest").json()
    assert d["month"] == "2026-10"
    assert client.get("/api/digest", params={"month": "2026-09"}).json()["month"] == "2026-09"
    assert client.get("/api/digest", params={"month": "2026-13"}).status_code == 422


def test_export_csv(client):
    r = client.get("/api/export", params={"status": "all"})
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.lstrip("\ufeff").strip().split("\r\n")
    assert lines[0].startswith("date,vendor,category,amount")
    assert len(lines) == 29


def test_splits_roundtrip(client):
    tx = client.get("/api/ledger", params={"q": "bookmyshow"}).json()["transactions"][0]
    seeded = client.get(f"/api/splits/{tx['id']}").json()["splits"]
    assert sorted(s["participant"] for s in seeded) == ["Aman", "Priya", "Riya"]
    replaced = client.post(
        "/api/splits",
        json={"transaction_id": tx["id"], "participants": [{"participant": "Aman", "share": 480}]},
    ).json()["splits"]
    assert len(replaced) == 1
    missing = client.post(
        "/api/splits",
        json={"transaction_id": "x", "participants": [{"participant": "A", "share": 1}]},
    )
    assert missing.status_code == 404


def test_settle_endpoint_validation(client):
    body = {
        "participants": ["A", "B"],
        "expenses": [{"paid_by": "Z", "amount": 10, "split_among": ["A"]}],
    }
    assert client.post("/api/splits/settle", json=body).status_code == 422
    assert client.post("/api/splits/settle", json={"participants": []}).status_code == 422


def test_query_falls_back_to_rules_without_ollama(client):
    r = client.post("/api/query", json={"question": "What are my top 3 merchants?"}).json()
    assert r["engine"] == "rules"
    assert "Top merchants" in r["answer"]
    assert client.post("/api/query", json={"question": "   "}).status_code == 422

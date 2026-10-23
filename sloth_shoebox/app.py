"""FastAPI app: the single-page site plus the JSON API behind the live demo."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__, content, ledger
from .categorize import CATEGORY_KEYS, category_label
from .config import PACKAGE_DIR, Settings
from .dedupe import content_hash
from .digest import compute_digest, default_month, r2
from .docs import load_docs
from .export import to_csv
from .ingest import delete_artifact, ingest, list_artifacts
from .parser import stand_in_parse, vlm_parse
from .query import answer
from .samples import SAMPLES, SAMPLES_BY_ID, sample_for_bytes
from .schema import (
    QueryRequest,
    SampleIngest,
    SettleRequest,
    SplitsIn,
    TransactionPatch,
)
from .seed import seed
from .splits import settle

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"

# The parse path never leaves the machine, and neither does the page.
CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; "
    "base-uri 'none'; form-action 'self'"
)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    with ledger.session(request.app.state.settings.db_path) as conn:
        yield conn


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
Cfg = Annotated[Settings, Depends(get_settings)]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ledger.init_db(settings.db_path)
        if settings.autoseed:
            with ledger.session(settings.db_path) as conn:
                if ledger.is_empty(conn):
                    seed(conn)
        yield

    app = FastAPI(
        title="The Sloth Shoebox",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,  # the stock Swagger page loads scripts from a CDN
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.docs = load_docs(settings.docs_path)
    templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    # ------------------------------------------------------------------ pages
    @app.get("/", include_in_schema=False)
    def home(request: Request):
        docs = app.state.docs
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "version": ".".join(__version__.split(".")[:2]),
                "samples": [s.public() for s in SAMPLES],
                "categories": [(k, category_label(k)) for k in CATEGORY_KEYS],
                "docs": docs,
                "c": content,
            },
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/samples")
    def samples() -> dict[str, Any]:
        return {"samples": [s.public() for s in SAMPLES]}

    # ----------------------------------------------------------------- ledger
    def _filter(
        category: str | None,
        status: str | None,
        date_from: str | None,
        date_to: str | None,
        q: str | None,
    ) -> ledger.TxFilter:
        return ledger.TxFilter(category, status, date_from, date_to, q)

    @app.get("/api/ledger")
    def get_ledger(
        conn: Conn,
        category: str | None = None,
        status: str | None = None,
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
        q: str | None = None,
        limit: Annotated[int, Query(ge=1, le=10000)] = 200,
    ) -> dict[str, Any]:
        flt = _filter(category, status, date_from, date_to, q)
        rows = ledger.list_transactions(conn, flt, limit)
        by_category: dict[str, float] = {}
        for r in rows:
            by_category[r["category"]] = r2(by_category.get(r["category"], 0) + r["amount"])
        return {
            "transactions": rows,
            "total": len(rows),
            "total_count": ledger.count_transactions(conn, flt),
            "totals": {
                "count": len(rows),
                "sum": r2(sum(r["amount"] for r in rows)),
                "by_category": by_category,
            },
            "digest_month": default_month(ledger.digest_rows(conn)),
        }

    @app.get("/api/ledger/{tx_id}")
    def get_one(tx_id: str, conn: Conn) -> dict[str, Any]:
        tx = ledger.get_transaction(conn, tx_id)
        if tx is None:
            raise HTTPException(404, "Transaction not found")
        return {"transaction": tx, "splits": ledger.splits_for(conn, tx_id)}

    @app.patch("/api/ledger/{tx_id}")
    def patch_one(tx_id: str, body: TransactionPatch, conn: Conn) -> dict[str, Any]:
        changes = body.model_dump(exclude_unset=True)
        for required in ("category", "status", "review_flag"):
            if changes.get(required, "") is None:
                del changes[required]
        tx = ledger.update_transaction(conn, tx_id, changes)
        if tx is None:
            raise HTTPException(404, "Transaction not found")
        return {"transaction": tx}

    @app.delete("/api/ledger/{tx_id}")
    def delete_one(tx_id: str, conn: Conn) -> dict[str, Any]:
        if not ledger.delete_transaction(conn, tx_id):
            raise HTTPException(404, "Transaction not found")
        return {"ok": True, "id": tx_id}

    @app.get("/api/export")
    def export(
        conn: Conn,
        category: str | None = None,
        status: str | None = None,
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
        q: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100000)] = 10000,
    ) -> Response:
        rows = ledger.list_transactions(
            conn, _filter(category, status, date_from, date_to, q), limit
        )
        return Response(
            to_csv(rows),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="sloth-shoebox-ledger.csv"'},
        )

    # ----------------------------------------------------------------- ingest
    @app.post("/api/ingest")
    def ingest_sample(body: SampleIngest, conn: Conn) -> dict[str, Any]:
        sample = SAMPLES_BY_ID.get(body.sample_id)
        if sample is None:
            raise HTTPException(404, "Unknown sample")
        return ingest(
            conn,
            file_name=sample.source_file,
            file_type="image",
            content_hash=sample.content_hash,
            parse=dict(sample.parse),
        )

    @app.post("/api/ingest/upload")
    def ingest_upload(conn: Conn, cfg: Cfg, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File is larger than 15 MB")
        if not data:
            raise HTTPException(400, "File is empty")
        name = Path(file.filename or "upload").name[:120] or "upload"
        file_type = "pdf" if name.lower().endswith(".pdf") else "image"

        known = sample_for_bytes(data)
        if known is not None:
            return ingest(
                conn,
                file_name=known.source_file,
                file_type="image",
                content_hash=known.content_hash,
                parse=dict(known.parse),
            )
        digest = content_hash(data)
        if cfg.parser == "ollama":
            attempt = vlm_parse(cfg, name, data)
            return ingest(
                conn,
                file_name=name,
                file_type=file_type,
                content_hash=digest,
                parse=attempt.parse,
                raw_output=attempt.raw,
                parse_error=attempt.error,
            )
        return ingest(
            conn,
            file_name=name,
            file_type=file_type,
            content_hash=digest,
            parse=stand_in_parse(name, digest),
        )

    @app.get("/api/inbox")
    def inbox(conn: Conn) -> dict[str, Any]:
        artifacts = list_artifacts(conn)
        return {"artifacts": artifacts, "total": len(artifacts)}

    @app.delete("/api/inbox/{artifact_id}")
    def inbox_delete(artifact_id: str, conn: Conn) -> dict[str, Any]:
        if not delete_artifact(conn, artifact_id):
            raise HTTPException(404, "Artifact not found")
        return {"ok": True, "id": artifact_id}

    # ----------------------------------------------------------------- digest
    @app.get("/api/digest")
    def get_digest(
        conn: Conn, month: Annotated[str | None, Query(pattern=MONTH_PATTERN)] = None
    ) -> dict[str, Any]:
        rows = ledger.digest_rows(conn)
        return compute_digest(rows, month or default_month(rows))

    # ------------------------------------------------------------------ query
    @app.post("/api/query")
    def post_query(body: QueryRequest, conn: Conn, cfg: Cfg) -> dict[str, Any]:
        return answer(conn, cfg, body.question)

    # ----------------------------------------------------------------- splits
    @app.post("/api/splits")
    def post_splits(body: SplitsIn, conn: Conn) -> dict[str, Any]:
        if ledger.get_transaction(conn, body.transaction_id) is None:
            raise HTTPException(404, "Transaction not found")
        shares = [(p.participant, p.share) for p in body.participants]
        return {"splits": ledger.replace_splits(conn, body.transaction_id, shares)}

    @app.post("/api/splits/settle")
    def post_settle(body: SettleRequest) -> dict[str, Any]:
        return settle(body)

    @app.get("/api/splits/{tx_id}")
    def get_splits(tx_id: str, conn: Conn) -> dict[str, Any]:
        tx = ledger.get_transaction(conn, tx_id)
        if tx is None:
            raise HTTPException(404, "Transaction not found")
        return {"transaction": tx, "splits": ledger.splits_for(conn, tx_id)}

    @app.exception_handler(sqlite3.Error)
    async def db_error(_: Request, exc: sqlite3.Error) -> JSONResponse:
        return JSONResponse({"detail": f"Database error: {exc}"}, status_code=500)

    return app


app = create_app()

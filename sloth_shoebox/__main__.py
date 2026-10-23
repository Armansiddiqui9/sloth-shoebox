"""`python -m sloth_shoebox [serve|seed]`"""

from __future__ import annotations

import argparse

import uvicorn

from . import ledger
from .config import Settings
from .seed import seed


def main() -> None:
    parser = argparse.ArgumentParser(prog="sloth_shoebox", description="The Sloth Shoebox")
    parser.add_argument("command", nargs="?", choices=["serve", "seed"], default="serve")
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "seed":
        ledger.init_db(settings.db_path)
        with ledger.session(settings.db_path) as conn:
            count = seed(conn)
        print(f"Seeded {count} transactions into {settings.db_path}")
        return

    print(
        f"The Sloth Shoebox on http://{settings.host}:{settings.port}  (ledger: {settings.db_path})"
    )
    uvicorn.run("sloth_shoebox.app:app", host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()

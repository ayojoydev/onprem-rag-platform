import argparse

import uvicorn

from .app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the synthetic retail API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--database", help="SQLite file; otherwise SIMULATOR_DATABASE_PATH or data/business-api.sqlite3")
    parser.add_argument("--no-seed", action="store_true", help="Initialize a new empty database without demo fixtures")
    args = parser.parse_args()
    application = create_app(database_path=args.database, seed_demo=False if args.no_seed else None)
    uvicorn.run(application, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

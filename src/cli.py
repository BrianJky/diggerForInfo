import argparse
import logging
from pathlib import Path

import yaml

from src.collector import collect_items, create_session
from src.digest import generate_digest
from src.filtering import apply_filters
from src.parser import fetch_content
from src.store import init_db, insert_article, fetch_recent, stats_recent


def setup_logging(data_dir: Path, log_file: str) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / log_file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def load_config(path: str | None) -> dict:
    if path:
        config_path = Path(path)
    else:
        config_path = Path("config.yaml")
    if not config_path.exists():
        raise FileNotFoundError("Missing config.yaml (copy from config.example.yaml)")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def run_collect(config: dict) -> None:
    app = config.get("app", {})
    data_dir = Path(app.get("data_dir", "data"))
    setup_logging(data_dir, app.get("log_file", "app.log"))

    session = create_session(app.get("request_timeout", 10), app.get("max_retries", 3))
    items = collect_items(session, config)

    db_path = data_dir / "articles.db"
    conn = init_db(db_path)

    for item in items:
        content_data = fetch_content(
            session,
            item.get("url", ""),
            app.get("request_timeout", 10),
            app.get("sleep_min", 0.5),
            app.get("sleep_max", 1.5),
        )
        title = item.get("title") or content_data.get("title")
        author = content_data.get("author")
        tags = content_data.get("tags", [])
        content = content_data.get("content", "")

        included, reason, matched_keywords = apply_filters(
            title, content, tags, author, config
        )
        record = {
            "url": item.get("url"),
            "title": title,
            "author": author,
            "published": item.get("published"),
            "summary": item.get("summary", ""),
            "content": content,
            "tags": tags,
            "source": item.get("source"),
            "matched_keywords": matched_keywords,
            "included": included,
            "filter_reason": reason,
        }
        insert_article(conn, record)


def run_digest(config: dict, days: int, use_ai: bool) -> None:
    app = config.get("app", {})
    data_dir = Path(app.get("data_dir", "data"))
    setup_logging(data_dir, app.get("log_file", "app.log"))
    db_path = data_dir / "articles.db"
    conn = init_db(db_path)

    records = fetch_recent(conn, days)
    model = config.get("ai", {}).get("model", "gpt-4o-mini")
    generate_digest(records, data_dir, use_ai, model)


def run_stats(config: dict, days: int) -> None:
    app = config.get("app", {})
    data_dir = Path(app.get("data_dir", "data"))
    setup_logging(data_dir, app.get("log_file", "app.log"))
    db_path = data_dir / "articles.db"
    conn = init_db(db_path)

    stats = stats_recent(conn, days)
    logging.info("Stats (last %s days):", days)
    logging.info("Total: %s", stats["total"])
    logging.info("Included: %s", stats["included"])
    logging.info("Excluded: %s", stats["excluded"])
    logging.info("Exclude reasons: %s", stats["reasons"])
    logging.info("Top keywords: %s", list(stats["keywords"].items())[:10])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Juejin AI Weekly Digest")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("collect", help="Collect daily articles")

    digest_parser = subparsers.add_parser("digest", help="Generate weekly digest")
    digest_parser.add_argument("--days", type=int, default=7)
    digest_parser.add_argument("--ai", action="store_true", help="Use AI summarization")

    stats_parser = subparsers.add_parser("stats", help="Show stats")
    stats_parser.add_argument("--days", type=int, default=7)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "collect":
        run_collect(config)
    elif args.command == "digest":
        run_digest(config, args.days, args.ai)
    elif args.command == "stats":
        run_stats(config, args.days)


if __name__ == "__main__":
    main()

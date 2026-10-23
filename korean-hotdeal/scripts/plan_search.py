#!/usr/bin/env python3
"""Create source-scoped search batches and an unsearched coverage ledger."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def positive_days(value):
    days = int(value)
    if days < 1:
        raise argparse.ArgumentTypeError("recency-days must be positive")
    return days


def build_plan(catalog, keywords, batch_size=4, recency_days=3):
    sources = catalog["sources"]
    ids = [source["id"] for source in sources]
    if len(sources) != 27 or len(set(ids)) != 27:
        raise ValueError("The source catalog must contain 27 unique source IDs")
    terms = list(dict.fromkeys(term.strip() for term in keywords if term.strip()))
    if not terms:
        raise ValueError("Provide at least one non-empty product keyword")
    # Keep every keyword a literal phrase, including multiword model names.
    expression = " OR ".join('"' + term.replace('"', ' ').replace('\\', ' ').strip() + '"' for term in terms)
    queries = [
        {"q": f'{source["search_scope"]} ({expression})', "recency": recency_days}
        for source in sources
    ]
    return {
        "generated_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
        "plan_only": True,
        "keywords": terms,
        "query_batches": [queries[start:start + batch_size] for start in range(0, len(queries), batch_size)],
        "coverage": [
            {
                "source_id": source["id"],
                "name": source["name"],
                "board_url": source["board_url"],
                "query": queries[index]["q"],
                "status": "not_searched",
                "search_completed": False,
                "inspected_range": None,
                "checked_at": None,
                "method": None,
                "candidate_count": None,
                "notes": "",
            }
            for index, source in enumerate(sources)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keywords", nargs="+", help="Product names or synonyms; quote multiword names")
    parser.add_argument("--batch-size", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--recency-days", type=positive_days, default=3)
    parser.add_argument("--output", type=Path, help="Write UTF-8 JSON here instead of stdout")
    args = parser.parse_args()
    source_path = Path(__file__).resolve().parents[1] / "references" / "sources.json"
    try:
        catalog = json.loads(source_path.read_text(encoding="utf-8"))
        plan = build_plan(catalog, args.keywords, args.batch_size, args.recency_days)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
        print(f"Created search plan for {len(plan['coverage'])} sources: {args.output}")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()

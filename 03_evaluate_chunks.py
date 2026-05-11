from __future__ import annotations

import argparse
from pathlib import Path

from rag_research_chunking import evaluate_chunks
from rag_research_chunking.common import iter_json_files, read_json, setup_logger, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate relationship-aware research-paper chunks.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--chunk-size", type=int, default=640)
    parser.add_argument("--table-chunk-size", type=int, default=768)
    parser.add_argument("--min-prose-tokens", type=int, default=80)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_file = (args.log_dir / "03_evaluate_chunks.log") if args.log_dir else None
    logger = setup_logger("evaluate", log_file, args.verbose)
    args.output.mkdir(parents=True, exist_ok=True)

    reports = []
    files = iter_json_files(args.input)
    logger.info("Chunk files discovered: %d", len(files))

    for path in files:
        if path.name.startswith("_chunk_report"):
            continue
        logger.info("Evaluating file: %s", path.name)
        try:
            chunks = read_json(path)
            if not isinstance(chunks, list):
                raise ValueError("Chunk file must contain a list of chunks")
            report = evaluate_chunks(chunks, args.chunk_size, args.table_chunk_size, args.min_prose_tokens)
            report["file"] = path.name
            reports.append(report)
            logger.info(
                "Evaluated %s | status=%s | chunks=%d | by_type=%s | equation=%s | table=%s | figure=%s | relations=%s",
                path.name,
                report["overall_status"],
                report["total_chunks"],
                report["chunk_count_by_type"],
                report["equation_context"]["status"],
                report["table_quality"]["status"],
                report["figure_quality"]["status"],
                report["relationship_metadata"]["status"],
            )
        except Exception as exc:
            logger.exception("Failed evaluating %s: %s", path.name, exc)
            reports.append({"file": path.name, "status": "ERROR", "error": str(exc)})

    summary = {
        "total_files": len(reports),
        "status_counts": {},
        "reports": reports,
    }
    for report in reports:
        status = report.get("overall_status", report.get("status", "UNKNOWN"))
        summary["status_counts"][status] = summary["status_counts"].get(status, 0) + 1

    out_path = args.output / "_evaluation_report.json"
    write_json(out_path, summary)
    logger.info("Evaluation report written: %s", out_path)
    logger.info("Status counts: %s", summary["status_counts"])


if __name__ == "__main__":
    main()

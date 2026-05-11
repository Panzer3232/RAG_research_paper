from __future__ import annotations

import argparse
from pathlib import Path

from rag_research_chunking import ChunkConfig, chunk_document
from rag_research_chunking.common import iter_json_files, read_json, setup_logger, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create relationship-aware chunks from normalized research-paper JSON files.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--chunk-size", type=int, default=640)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--table-chunk-size", type=int, default=768)
    parser.add_argument("--min-prose-tokens", type=int, default=80)
    parser.add_argument("--max-context-blocks", type=int, default=2)
    parser.add_argument("--no-table-splitting", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_file = (args.log_dir / "02_chunk_papers.log") if args.log_dir else None
    logger = setup_logger("chunk", log_file, args.verbose)
    args.output.mkdir(parents=True, exist_ok=True)

    config = ChunkConfig(
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        table_chunk_size=args.table_chunk_size,
        min_prose_tokens=args.min_prose_tokens,
        max_context_blocks=args.max_context_blocks,
        split_long_tables=not args.no_table_splitting,
    )

    reports = []
    files = iter_json_files(args.input)
    logger.info("Input files discovered: %d", len(files))
    logger.info("Chunk config: %s", config)

    for path in files:
        if path.name.startswith("_prepare_report"):
            continue
        logger.info("Chunking file: %s", path.name)
        try:
            data = read_json(path)
            chunks, report = chunk_document(data, config)
            out_path = args.output / path.name
            write_json(out_path, chunks)
            report["file"] = path.name
            reports.append(report)
            logger.info(
                "Chunked %s | total=%d | by_type=%s | flags=%s | backend=%s",
                path.name,
                report["total_chunks"],
                report["chunks_by_type"],
                report["quality_flags"],
                report["splitter_backend"],
            )
        except Exception as exc:
            logger.exception("Failed chunking %s: %s", path.name, exc)
            reports.append({"file": path.name, "status": "ERROR", "error": str(exc)})

    report_path = args.output / "_chunk_report.json"
    write_json(report_path, reports)
    logger.info("Chunk report written: %s", report_path)


if __name__ == "__main__":
    main()

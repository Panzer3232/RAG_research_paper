from __future__ import annotations

import argparse
from pathlib import Path

from rag_research_chunking.common import iter_json_files, read_json, setup_logger, write_json
from rag_research_chunking.filters import prepare_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize and filter research-paper JSON files before chunking.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--log-dir", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_file = (args.log_dir / "01_prepare_papers.log") if args.log_dir else None
    logger = setup_logger("prepare", log_file, args.verbose)
    args.output.mkdir(parents=True, exist_ok=True)

    reports = []
    files = iter_json_files(args.input)
    logger.info("Input files discovered: %d", len(files))

    for path in files:
        logger.info("Preparing file: %s", path.name)
        try:
            data = read_json(path)
            prepared, report = prepare_document(data, path.name)
            out_path = args.output / path.name
            write_json(out_path, prepared)
            reports.append(report)
            logger.info(
                "Prepared %s | sections %d -> %d | blocks %d -> %d | drops=%s",
                path.name,
                report["input_sections"],
                report["kept_sections"],
                report["input_blocks"],
                report["kept_blocks"],
                report["block_drops"],
            )
        except Exception as exc:
            logger.exception("Failed preparing %s: %s", path.name, exc)
            reports.append({"file": path.name, "status": "ERROR", "error": str(exc)})

    report_path = args.output / "_prepare_report.json"
    write_json(report_path, reports)
    logger.info("Prepare report written: %s", report_path)


if __name__ == "__main__":
    main()

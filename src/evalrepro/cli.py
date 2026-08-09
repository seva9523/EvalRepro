"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from evalrepro import __version__
from evalrepro.adapters.inspect import inspect_source
from evalrepro.adapters.jsonl import jsonl_source
from evalrepro.compare import compare_manifests
from evalrepro.errors import EvalReproError
from evalrepro.manifest import build_manifest, read_manifest, write_manifest
from evalrepro.report import render_markdown, render_text


def _fields(raw: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not values:
        raise argparse.ArgumentTypeError("At least one semantic field is required.")
    if len(values) != len(set(values)):
        raise argparse.ArgumentTypeError("Semantic field names must be unique.")
    return values


def _json_object(raw: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("Value must decode to a JSON object.")
    return value


def _positive_limit(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Limit must be greater than zero.")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalrepro",
        description="Detect semantic drift in AI evaluation inputs and contracts.",
    )
    parser.add_argument("--version", action="version", version=f"evalrepro {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    snapshot = commands.add_parser("snapshot", help="Create a hash-only evaluation manifest")
    snapshot_adapters = snapshot.add_subparsers(dest="adapter", required=True)

    jsonl = snapshot_adapters.add_parser("jsonl", help="Snapshot a JSON Lines evaluation file")
    jsonl.add_argument("source", type=Path)
    jsonl.add_argument("--output", "-o", type=Path, required=True)
    jsonl.add_argument("--name", default="jsonl-evaluation")
    jsonl.add_argument("--fields", type=_fields, default=("input", "target", "choices", "metadata"))
    jsonl.add_argument("--id-field", default="id")
    jsonl.add_argument("--limit", type=_positive_limit)

    inspect = snapshot_adapters.add_parser("inspect", help="Snapshot an Inspect task dataset")
    inspect.add_argument("task", help="Task factory as package.module:function")
    inspect.add_argument("--kwargs", type=_json_object, default={})
    inspect.add_argument("--output", "-o", type=Path, required=True)
    inspect.add_argument(
        "--fields", type=_fields, default=("input", "target", "choices", "metadata")
    )
    inspect.add_argument("--id-field", default="id")
    inspect.add_argument("--limit", type=_positive_limit)

    compare = commands.add_parser("compare", help="Compare two manifests")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--json", dest="json_output", type=Path)
    compare.add_argument("--markdown", type=Path)
    compare.add_argument("--quiet", action="store_true")
    compare.add_argument(
        "--allow-drift",
        action="store_true",
        help="Return exit code 0 even when drift is detected",
    )

    validate = commands.add_parser("validate", help="Validate one manifest")
    validate.add_argument("manifest", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot" and args.adapter == "jsonl":
            source = jsonl_source(
                args.source,
                name=args.name,
                fields=args.fields,
                id_field=args.id_field or None,
            )
            write_manifest(args.output, build_manifest(source, args.limit))
            print(f"Wrote {args.output}")
            return 0

        if args.command == "snapshot" and args.adapter == "inspect":
            source = inspect_source(
                args.task,
                kwargs=args.kwargs,
                fields=args.fields,
                id_field=args.id_field or None,
            )
            write_manifest(args.output, build_manifest(source, args.limit))
            print(f"Wrote {args.output}")
            return 0

        if args.command == "compare":
            comparison = compare_manifests(args.baseline, args.candidate)
            if args.json_output:
                args.json_output.parent.mkdir(parents=True, exist_ok=True)
                args.json_output.write_text(
                    json.dumps(comparison.to_dict(), indent=2) + "\n", encoding="utf-8"
                )
            if args.markdown:
                args.markdown.parent.mkdir(parents=True, exist_ok=True)
                args.markdown.write_text(render_markdown(comparison), encoding="utf-8")
            if not args.quiet:
                print(render_text(comparison), end="")
            return 0 if comparison.reproducible or args.allow_drift else 2

        if args.command == "validate":
            read_manifest(args.manifest)
            print(f"Valid EvalRepro manifest: {args.manifest}")
            return 0
    except EvalReproError as exc:
        print(f"evalrepro: {exc}", file=sys.stderr)
        return 3

    parser.error("Unsupported command")
    return 3


def entrypoint() -> None:
    raise SystemExit(main())

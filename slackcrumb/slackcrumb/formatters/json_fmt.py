"""Structured JSON output formatter."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..config import OutputConfig
from ..models import ExportResult


def format_json(result: ExportResult) -> str:
    """Format an ExportResult as a JSON string."""
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def write_json(result: ExportResult, config: OutputConfig,
               date_str: str | None = None) -> Path:
    """Write ExportResult to a JSON file and return the path."""
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = date_str or datetime.now().strftime("%Y%m%d")
    channels_str = "_".join(c.name for c in result.channels[:3])
    if len(result.channels) > 3:
        channels_str += f"_+{len(result.channels) - 3}"

    filename = config.filename_template.format(
        channel=channels_str or "export",
        date=date_str,
    )
    if not filename.endswith(".json"):
        filename += ".json"

    path = output_dir / filename
    path.write_text(format_json(result), encoding="utf-8")
    return path

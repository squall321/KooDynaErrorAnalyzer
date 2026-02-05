"""JSON report writer for the analysis results."""

import json
import dataclasses
from enum import Enum
from pathlib import Path

from koodyna.models import Report


class ReportEncoder(json.JSONEncoder):
    """Custom JSON encoder for Report dataclasses."""

    def default(self, obj):
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, float):
            if obj != obj:  # NaN check
                return None
            if abs(obj) > 0 and (abs(obj) < 1e-10 or abs(obj) > 1e10):
                return f"{obj:.6E}"
        return super().default(obj)


def report_to_dict(report: Report) -> dict:
    """Convert Report to a JSON-serializable dictionary."""

    def convert(obj):
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            result = {}
            for f in dataclasses.fields(obj):
                value = getattr(obj, f.name)
                result[f.name] = convert(value)
            return result
        elif isinstance(obj, list):
            return [convert(item) for item in obj]
        elif isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        elif isinstance(obj, set):
            return sorted(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, Path):
            return str(obj)
        return obj

    return convert(report)


def write_json_report(report: Report, filepath: Path):
    """Write the report as a JSON file."""
    data = report_to_dict(report)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=ReportEncoder)

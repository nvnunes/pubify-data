from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast

WORKSPACE_CONFIG_FILENAME = "pubify.yaml"


@dataclass(frozen=True)
class PubifyConfig:
    """Raw shared workspace config loaded from ``pubify.yaml``."""

    workspace_root: Path
    raw: dict[str, object]

    def section(self, name: str) -> dict[str, object]:
        value = self.raw.get(name, {})
        if not isinstance(value, dict):
            raise ValueError(f"{self.workspace_root / WORKSPACE_CONFIG_FILENAME}: {name} must be a mapping")
        return dict(value)


def find_workspace_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` until a ``pubify.yaml`` workspace root is found."""

    current = (start or Path.cwd()).resolve()
    for path in (current, *current.parents):
        if (path / WORKSPACE_CONFIG_FILENAME).exists():
            return path
    raise FileNotFoundError("Could not locate workspace root from current working directory")


def load_pubify_config(workspace_root: Path) -> PubifyConfig:
    """Load raw namespaced workspace config from ``pubify.yaml``."""

    root = workspace_root.resolve()
    config_path = root / WORKSPACE_CONFIG_FILENAME
    if not config_path.exists():
        raise FileNotFoundError(f"Missing workspace config: {config_path}")
    return PubifyConfig(workspace_root=root, raw=parse_simple_yaml(config_path.read_text(encoding="utf-8")))


def load_config_section(workspace_root: Path, section_name: str) -> dict[str, object]:
    """Load one namespaced section from ``pubify.yaml``."""

    return load_pubify_config(workspace_root).section(section_name)


def resolve_workspace_relative_path(
    section: dict[str, object],
    config_path: Path,
    key: str,
    *,
    allow_blank: bool = False,
) -> Path | None:
    """Resolve one downstream-owned root key relative to the workspace config."""

    value = section.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{config_path}: {key} must be a string")
    if value == "":
        if allow_blank:
            return None
        raise ValueError(f"{config_path}: {key} must be a non-empty string")
    resolved = Path(value).expanduser()
    if not resolved.is_absolute():
        resolved = (config_path.parent / resolved).resolve()
    return resolved


def parse_simple_yaml(text: str) -> dict[str, object]:
    """Parse the small YAML subset used by pubify config files."""

    lines = _clean_yaml_lines(text)
    parsed, next_index = _parse_mapping(lines, 0, 0)
    if next_index != len(lines):
        raise ValueError(f"Unexpected trailing YAML content near line {next_index + 1}")
    return parsed


def _clean_yaml_lines(text: str) -> list[tuple[int, str]]:
    cleaned: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        cleaned.append((indent, line.strip()))
    return cleaned


def _parse_mapping(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[dict[str, object], int]:
    data: dict[str, object] = {}
    index = start
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError(f"Invalid indentation near line {index + 1}")
        if content.startswith("- "):
            raise ValueError(f"Unexpected list item near line {index + 1}")
        if ":" not in content:
            raise ValueError(f"Invalid YAML line near line {index + 1}: {content!r}")
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid YAML key near line {index + 1}")
        if value:
            data[key] = _parse_scalar(value)
            index += 1
            continue
        index += 1
        if index >= len(lines) or lines[index][0] <= current_indent:
            data[key] = {}
            continue
        child_indent, child_content = lines[index]
        if child_content.startswith("- "):
            value_list, index = _parse_list(lines, index, child_indent)
            data[key] = value_list
            continue
        child_map, index = _parse_mapping(lines, index, child_indent)
        data[key] = child_map
    return data, index


def _parse_list(lines: list[tuple[int, str]], start: int, indent: int) -> tuple[list[object], int]:
    values: list[object] = []
    index = start
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent or not content.startswith("- "):
            raise ValueError(f"Invalid list indentation near line {index + 1}")
        item = content[2:].strip()
        if not item:
            raise ValueError(f"List items must be scalar values near line {index + 1}")
        values.append(_parse_scalar(item))
        index += 1
    return values, index


def _parse_scalar(value: str) -> object:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    if value.startswith(("'", '"')):
        return ast.literal_eval(value)
    if value.startswith("[") and value.endswith("]"):
        parsed = ast.literal_eval(value)
        if not isinstance(parsed, list):
            raise ValueError(f"Expected list literal, got {value!r}")
        return parsed
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value

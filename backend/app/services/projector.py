"""
Configurable output projection layer (the Required Twist).

Takes a canonical profile dict and an OutputConfig and emits a projected dict.
Supported path syntax:
  full_name           — direct field
  location.city       — nested field
  emails[0]           — first element of a list
  skills[].name       — extract 'name' from every item in a list
"""
import re
from typing import Any
from app.schemas import OutputConfig
from app.services.normalizer import normalize_skill


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _resolve(data: Any, path: str) -> Any:
    # skills[].name  →  list of extracted sub-values
    m = re.match(r'^(\w+)\[\]\.(.+)$', path)
    if m:
        field, subpath = m.groups()
        arr = data.get(field, []) if isinstance(data, dict) else []
        if not isinstance(arr, list):
            return []
        return [_resolve(item, subpath) for item in arr if item is not None]

    # emails[0]  →  single element
    m = re.match(r'^(\w+)\[(\d+)\]$', path)
    if m:
        field, idx = m.group(1), int(m.group(2))
        arr = data.get(field, []) if isinstance(data, dict) else []
        return arr[idx] if isinstance(arr, list) and idx < len(arr) else None

    # location.city  →  nested
    if '.' in path:
        first, rest = path.split('.', 1)
        parent = data.get(first) if isinstance(data, dict) else None
        if isinstance(parent, dict):
            return _resolve(parent, rest)
        return None

    return data.get(path) if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize(value: Any, mode: str | None) -> Any:
    if mode is None or value is None:
        return value
    mode = mode.upper()
    if mode == "E164":
        return value  # already E.164 from the normalizer stage
    if mode == "CANONICAL":
        if isinstance(value, list):
            return [normalize_skill(v) if isinstance(v, str) else v for v in value if v]
        return normalize_skill(value) if isinstance(value, str) else value
    if mode == "LOWERCASE":
        if isinstance(value, list):
            return [v.lower() if isinstance(v, str) else v for v in value]
        return value.lower() if isinstance(value, str) else value
    if mode == "UPPERCASE":
        if isinstance(value, list):
            return [v.upper() if isinstance(v, str) else v for v in value]
        return value.upper() if isinstance(value, str) else value
    return value


def _is_empty(v: Any) -> bool:
    return v is None or v == [] or v == {} or v == ""


# ---------------------------------------------------------------------------
# Main projection function
# ---------------------------------------------------------------------------

def project_profile(canonical: dict, config: OutputConfig) -> dict:
    """Apply OutputConfig to a canonical profile and return the projected dict."""

    if not config.fields:
        # No field selection — return full canonical, respecting toggles
        result = {k: v for k, v in canonical.items()}
        if not config.include_confidence:
            result.pop("overall_confidence", None)
            result.pop("fusion_score", None)
            for skill in result.get("skills", []):
                if isinstance(skill, dict):
                    skill.pop("confidence", None)
        if not config.include_provenance:
            result.pop("provenance", None)
        return result

    result: dict[str, Any] = {}
    errors: list[str] = []

    for fc in config.fields:
        source_path = fc.from_ if fc.from_ else fc.path
        value = _resolve(canonical, source_path)
        value = _normalize(value, fc.normalize)

        if _is_empty(value):
            if config.on_missing == "omit":
                continue
            elif config.on_missing == "error" and fc.required:
                errors.append(f"Required field '{fc.path}' (from '{source_path}') is missing or empty.")
            else:
                result[fc.path] = None
        else:
            result[fc.path] = value

    if errors:
        raise ValueError("; ".join(errors))

    if config.include_confidence:
        result["overall_confidence"] = canonical.get("overall_confidence")
        result["fusion_score"] = canonical.get("fusion_score")

    if config.include_provenance:
        result["provenance"] = canonical.get("provenance", [])

    return result

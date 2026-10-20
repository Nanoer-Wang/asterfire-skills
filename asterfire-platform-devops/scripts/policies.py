from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

SEMVER_RE = re.compile(r"^(?:v)?(\d+)\.(\d+)\.(\d+)$")


def slugify(value: str, max_len: int = 60) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"[-_.]{2,}", "-", value).strip("-._")
    return (value or "asterfire")[:max_len].rstrip("-._")


def pipeline_name(project: str, artifact: str, version: str, purpose: str = "build") -> str:
    """Every Yunxiao pipeline gets a concrete <=60-char name."""
    return slugify(f"asterfire-{project}-{artifact}-{version}-{purpose}", 60)


def choose_yunxiao_cluster(internet_required: bool) -> str:
    """User-defined policy: external network => Hong Kong, otherwise Beijing."""
    return "public/cn-hongkong" if internet_required else "public/cn-beijing"


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    m = SEMVER_RE.match(tag.strip())
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def next_image_tag(existing_tags: Iterable[str], *, overwrite: str | None = None) -> str:
    """First version 1.0.0; overwrite keeps tag; otherwise patch-bump highest semver."""
    if overwrite:
        return overwrite
    versions = [v for t in existing_tags if (v := parse_semver(t)) is not None]
    if not versions:
        return "1.0.0"
    major, minor, patch = max(versions)
    return f"{major}.{minor}.{patch + 1}"

_EXTERNAL_PATTERNS = [
    re.compile(r"\bapt(?:-get)?\s+(?:update|install)\b", re.I),
    re.compile(r"\byum\s+install\b", re.I),
    re.compile(r"\bdnf\s+install\b", re.I),
    re.compile(r"\bapk\s+add\b", re.I),
    re.compile(r"\bpip(?:3)?\s+install\b", re.I),
    re.compile(r"\bpoetry\s+install\b", re.I),
    re.compile(r"\bnpm\s+(?:ci|install)\b", re.I),
    re.compile(r"\byarn\s+(?:install)?\b", re.I),
    re.compile(r"\bpnpm\s+install\b", re.I),
    re.compile(r"\bgit\s+clone\s+https?://", re.I),
    re.compile(r"\b(?:curl|wget)\b.*https?://", re.I),
]

_DOMESTIC_REGISTRY_HINTS = (
    "registry.cn-",
    "cr.aliyuncs.com",
    "registry-vpc.cn-",
    "build-steps-public-registry.cn-",
)


def dockerfile_needs_external_network(path: str | Path) -> bool:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if any(p.search(line) for p in _EXTERNAL_PATTERNS):
            return True
        if line.upper().startswith("FROM "):
            image = line.split()[1]
            # Treat unqualified Docker Hub / non-mainland registries as external.
            if "/" not in image or ("." in image.split("/")[0] and not any(h in image for h in _DOMESTIC_REGISTRY_HINTS)):
                return True
    return False


def resolve_internet_requirement(value: str | bool, dockerfile: str | Path) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    if normalized != "auto":
        raise ValueError("internet_required must be auto/true/false")
    return dockerfile_needs_external_network(dockerfile)

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def load_standard_env(*starts: str | Path) -> list[Path]:
    """Load the nearest .env files without overriding process environment."""
    candidates: list[Path] = []
    seen: set[Path] = set()
    for start in starts:
        path = Path(start).resolve()
        if path.is_file():
            path = path.parent
        for parent in (path, *path.parents):
            candidate = parent / ".env"
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.is_file():
                candidates.append(candidate)
                break

    loaded: list[Path] = []
    for path in candidates:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            os.environ.setdefault(key, value)
        loaded.append(path)
    return loaded


def _coerce(value: str) -> Any:
    v = value.strip()
    if not v:
        return ""
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    low = v.lower()
    if low in {"true", "false"}:
        return low == "true"
    if low in {"null", "none", "~"}:
        return None
    try:
        return int(v)
    except ValueError:
        return v


def _simple_yaml(text: str) -> dict[str, Any]:
    """Tiny YAML subset parser for this skill's nested mapping template."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            raise ValueError(f"Unsupported YAML line: {raw}")
        key, value = line.split(":", 1)
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        key = key.strip()
        if value.strip() == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = _coerce(value)
    return root


def _expand_env(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(v) for v in obj]
    if isinstance(obj, str):
        return ENV_RE.sub(lambda m: os.getenv(m.group(1), ""), obj)
    return obj


def load_mapping(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    if text.lstrip().startswith("{"):
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(text) or {}
        except Exception:
            data = _simple_yaml(text)
    return _expand_env(data)


@dataclass
class AsterfireConfig:
    endpoint: str = "https://sidereus-ai.com/api/open/v1"
    token_env: str = "ASTERFIRE_TOKEN"

    @property
    def token(self) -> str:
        token = os.getenv(self.token_env, "")
        if not token:
            raise RuntimeError(f"Missing environment variable: {self.token_env}")
        return token


@dataclass
class BuildConfig:
    backend: str = "local"  # local | yunxiao
    platform: str = "linux/amd64"
    internet_required: str | bool = "auto"
    dockerfile: str = "Dockerfile"


@dataclass
class ACRConfig:
    edition: str = "enterprise"  # enterprise | personal
    region: str = "cn-hangzhou"
    instance_name: str = "asterfire"
    namespace: str = "asterfire"
    repository: str = ""
    registry_domain: str = ""
    username_env: str = "ACR_USERNAME"
    password_env: str = "ACR_PASSWORD"


@dataclass
class YunxiaoConfig:
    domain: str = ""
    mode: str = "center"  # center | region
    token_env: str = "YUNXIAO_TOKEN"
    organization_id_env: str = "YUNXIAO_ORGANIZATION_ID"
    codeup_repo: str = ""
    branch: str = "master"
    codeup_service_connection_env: str = "YUNXIAO_CODEUP_SERVICE_CONNECTION"
    acr_service_connection_env: str = "YUNXIAO_ACR_SERVICE_CONNECTION"
    build_container: str = "build-steps-public-registry.cn-beijing.cr.aliyuncs.com/build-steps/alinux3:latest"

    @property
    def token(self) -> str:
        token = os.getenv(self.token_env, "")
        if not token:
            raise RuntimeError(f"Missing environment variable: {self.token_env}")
        return token

    @property
    def organization_id(self) -> str:
        if self.mode == "region":
            return ""
        value = os.getenv(self.organization_id_env, "")
        if not value:
            raise RuntimeError(f"Missing environment variable: {self.organization_id_env}")
        return value

    @property
    def codeup_service_connection(self) -> str:
        return os.getenv(self.codeup_service_connection_env, "")

    @property
    def acr_service_connection(self) -> str:
        value = os.getenv(self.acr_service_connection_env, "")
        if not value:
            raise RuntimeError(f"Missing environment variable: {self.acr_service_connection_env}")
        return value


@dataclass
class Settings:
    asterfire: AsterfireConfig = field(default_factory=AsterfireConfig)
    build: BuildConfig = field(default_factory=BuildConfig)
    acr: ACRConfig = field(default_factory=ACRConfig)
    yunxiao: YunxiaoConfig = field(default_factory=YunxiaoConfig)


def load_settings(path: str | Path) -> Settings:
    d = load_mapping(path)
    return Settings(
        asterfire=AsterfireConfig(**d.get("asterfire", {})),
        build=BuildConfig(**d.get("build", {})),
        acr=ACRConfig(**d.get("acr", {})),
        yunxiao=YunxiaoConfig(**d.get("yunxiao", {})),
    )

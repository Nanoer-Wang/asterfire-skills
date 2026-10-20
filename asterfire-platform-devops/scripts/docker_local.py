from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    command: list[str]
    stdout: str = ""


class LocalDocker:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def _run(self, cmd: list[str], *, input_text: str | None = None) -> CommandResult:
        print("+", " ".join(shlex.quote(x) for x in cmd))
        if self.dry_run:
            return CommandResult(cmd)
        proc = subprocess.run(cmd, input=input_text, text=True, capture_output=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"Command failed: {cmd}")
        return CommandResult(cmd, proc.stdout.strip())

    def build(self, context: str | Path, dockerfile: str | Path, tag: str, platform: str = "linux/amd64") -> None:
        self._run(["docker", "buildx", "build", "--load", "--platform", platform, "-f", str(dockerfile), "-t", tag, str(context)])

    def login(self, registry: str, username_env: str, password_env: str) -> None:
        if self.dry_run:
            self._run(["docker", "login", registry, "-u", f"${{{username_env}}}", "--password-stdin"], input_text=f"${{{password_env}}}")
            return
        user = os.getenv(username_env, "")
        password = os.getenv(password_env, "")
        if not user or not password:
            raise RuntimeError(f"Missing {username_env} or {password_env}")
        self._run(["docker", "login", registry, "-u", user, "--password-stdin"], input_text=password)

    def tag(self, source: str, target: str) -> None:
        self._run(["docker", "tag", source, target])

    def push(self, image: str) -> None:
        self._run(["docker", "push", image])

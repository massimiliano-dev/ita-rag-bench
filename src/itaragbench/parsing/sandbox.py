"""Run a parser on an untrusted PDF in a separate, resource-limited process."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Only these variables reach the worker: no tokens, no API keys, no cloud credentials.
_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "HF_HOME",
    "HF_HUB_OFFLINE",
    "HF_HUB_DISABLE_TELEMETRY",
    "PYTORCH_ENABLE_MPS_FALLBACK",
    "OMP_NUM_THREADS",
)


class SandboxError(RuntimeError):
    pass


@dataclass
class SandboxLimits:
    timeout_s: float = 900.0
    max_mb: int = 4096


def _rss_mb(pid: int) -> float:
    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        ).stdout.strip()
        return int(out) / 1024 if out else 0.0
    except (ValueError, subprocess.SubprocessError):
        return 0.0


def _worker_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _ENV_ALLOWLIST}
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    env["PYTHONHASHSEED"] = "0"
    return env


def run_parser(
    parser: str,
    pdf: Path,
    first: int,
    last: int,
    limits: SandboxLimits,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse ``pdf`` pages [first, last] with ``parser`` in a sandboxed subprocess."""
    with tempfile.TemporaryDirectory(prefix="itarag-parse-") as tmp:
        out = Path(tmp) / "out.json"
        cmd = [
            sys.executable,
            "-I",
            "-m",
            "itaragbench.parsing.worker",
            parser,
            str(pdf.resolve()),
            str(first),
            str(last),
            str(out),
            "--max-mb",
            str(limits.max_mb),
            "--options",
            json.dumps(options or {}),
        ]
        # stderr goes to a file, not a pipe: a chatty parser (pypdf font warnings) would
        # otherwise fill the 64 KB pipe buffer and block forever.
        err_path = Path(tmp) / "stderr.log"
        err_fh = err_path.open("wb")
        proc = subprocess.Popen(
            cmd,
            cwd=tmp,
            env=_worker_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=err_fh,
            start_new_session=True,
        )
        t0 = time.monotonic()
        reason = ""
        peak = 0.0
        while proc.poll() is None:
            elapsed = time.monotonic() - t0
            rss = _rss_mb(proc.pid)
            peak = max(peak, rss)
            if elapsed > limits.timeout_s:
                reason = f"timeout after {limits.timeout_s:.0f}s"
            elif limits.max_mb > 0 and rss > limits.max_mb:
                reason = f"memory limit exceeded ({rss:.0f} MB > {limits.max_mb} MB)"
            if reason:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                err_fh.close()
                raise SandboxError(f"{parser} on {pdf.name}: {reason}")
            time.sleep(0.25)
        err_fh.close()
        if proc.returncode != 0:
            tail = err_path.read_bytes()[-2000:].decode("utf-8", "replace")
            raise SandboxError(f"{parser} on {pdf.name} exited with {proc.returncode}: {tail}")
        payload: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
        payload["peak_rss_mb"] = round(peak, 1)
        return payload

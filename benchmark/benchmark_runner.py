"""Benchmark LogScan DFA scanning against Python's re engine."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import subprocess
import sys
import time
from typing import Any

from core.hopcroft import minimize_dfa
from core.regex_parser import RegexParser
from core.scanner import DFAScanner
from core.subset import nfa_to_dfa
from core.thompson import regex_to_nfa


DEFAULT_BENCHMARK_TEXT = """2026-08-18 10:15:30 [INFO] System initialized.
2026-08-18 10:15:35 [ERROR] Database connection failed.
2026-08-18 10:15:40 [WARN] Retrying request.
"""


@dataclass
class PythonReResult:
    time_ms: float
    matches: int
    status: str = "ok"
    timed_out: bool = False
    error: str | None = None


@dataclass
class BenchmarkMetrics:
    pattern: str
    input_size_bytes: int
    input_size_label: str
    python_re_time_ms: float
    python_re_matches: int
    dfa_scanner_time_ms: float
    dfa_scanner_matches: int
    nfa_states: int
    dfa_states: int
    minimal_dfa_states: int
    speedup_ratio: float
    python_re_status: str = "ok"
    python_re_timed_out: bool = False
    python_re_error: str | None = None


@dataclass
class BenchmarkSuiteResult:
    pattern: str
    metrics: list[BenchmarkMetrics] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """Compare Python re finditer with LogScan DFA substring search."""

    def __init__(self, pattern: str, re_timeout_seconds: float = 2.0):
        self.pattern = pattern
        self.re_timeout_seconds = re_timeout_seconds
        self.ast = RegexParser(pattern).parse()
        self.nfa = regex_to_nfa(pattern)
        self.dfa = nfa_to_dfa(self.nfa)
        self.minimal_dfa = minimize_dfa(self.dfa)
        self.scanner = DFAScanner(self.minimal_dfa)

    def run_single(self, text: str, label: str = "") -> BenchmarkMetrics:
        """Benchmark one payload.

        DFA scanning uses non-overlapping longest matches so the match policy is
        comparable to Python re.finditer.
        """
        if text == "":
            text = DEFAULT_BENCHMARK_TEXT

        input_size_bytes = len(text.encode("utf-8"))
        input_size_label = label or format_bytes(input_size_bytes)

        python_re_result = _run_python_re_with_timeout(
            self.pattern,
            text,
            timeout_seconds=self.re_timeout_seconds,
        )

        start_dfa = time.perf_counter()
        dfa_matches = self.scanner.find_matches(text, overlapping=False, longest=True)
        dfa_time_ms = (time.perf_counter() - start_dfa) * 1000.0

        speedup = _speedup_ratio(python_re_result.time_ms, dfa_time_ms)

        return BenchmarkMetrics(
            pattern=self.pattern,
            input_size_bytes=input_size_bytes,
            input_size_label=input_size_label,
            python_re_time_ms=round(python_re_result.time_ms, 3),
            python_re_matches=python_re_result.matches,
            dfa_scanner_time_ms=round(dfa_time_ms, 3),
            dfa_scanner_matches=len(dfa_matches),
            nfa_states=len(self.nfa.states),
            dfa_states=len(self.dfa.states),
            minimal_dfa_states=len(self.minimal_dfa.states),
            speedup_ratio=round(speedup, 2),
            python_re_status=python_re_result.status,
            python_re_timed_out=python_re_result.timed_out,
            python_re_error=python_re_result.error,
        )

    def run_scaling_benchmark(
        self,
        base_text: str,
        scales: list[int] | None = None,
    ) -> BenchmarkSuiteResult:
        """Run benchmarks over repeated payload sizes."""
        if scales is None:
            scales = [1, 2, 5, 10, 20, 50, 100, 250, 500]

        seed_text = base_text or DEFAULT_BENCHMARK_TEXT
        metrics = [
            self.run_single((seed_text + "\n") * scale)
            for scale in scales
        ]

        state_reduction = (
            (1 - len(self.minimal_dfa.states) / len(self.dfa.states)) * 100
            if self.dfa.states
            else 0.0
        )

        summary = {
            "pattern": self.pattern,
            "nfa_states": len(self.nfa.states),
            "dfa_states": len(self.dfa.states),
            "minimal_dfa_states": len(self.minimal_dfa.states),
            "state_reduction_pct": round(state_reduction, 1),
            "python_re_timeouts": sum(metric.python_re_timed_out for metric in metrics),
        }
        return BenchmarkSuiteResult(pattern=self.pattern, metrics=metrics, summary=summary)


def run_benchmark(pattern: str, text: str) -> BenchmarkMetrics:
    return BenchmarkRunner(pattern).run_single(text)


def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _run_python_re_with_timeout(pattern: str, text: str, timeout_seconds: float) -> PythonReResult:
    payload = json.dumps({"pattern": pattern, "text": text})
    script = (
        "import json, re, sys, time\n"
        "payload = json.loads(sys.stdin.read())\n"
        "try:\n"
        "    compiled = re.compile(payload['pattern'])\n"
        "    start = time.perf_counter()\n"
        "    count = sum(1 for _ in compiled.finditer(payload['text']))\n"
        "    elapsed = (time.perf_counter() - start) * 1000.0\n"
        "    print(json.dumps({'status': 'ok', 'matches': count, 'time_ms': elapsed}))\n"
        "except re.error as exc:\n"
        "    print(json.dumps({'status': 're error', 'matches': 0, 'time_ms': 0.0, 'error': str(exc)}))\n"
    )

    try:
        completed = subprocess.run(
            [sys.executable, "-c", script],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return PythonReResult(
            time_ms=timeout_seconds * 1000.0,
            matches=0,
            status="timeout",
            timed_out=True,
            error=f"Python re exceeded {timeout_seconds:.1f}s timeout",
        )

    if completed.returncode != 0:
        return PythonReResult(
            time_ms=0.0,
            matches=0,
            status="error",
            error=completed.stderr.strip() or "Python re subprocess failed",
        )

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return PythonReResult(
            time_ms=0.0,
            matches=0,
            status="error",
            error=f"invalid benchmark subprocess output: {exc}",
        )

    return PythonReResult(
        time_ms=float(result.get("time_ms", 0.0)),
        matches=int(result.get("matches", 0)),
        status=str(result.get("status", "ok")),
        timed_out=False,
        error=result.get("error"),
    )


def _speedup_ratio(python_time_ms: float, dfa_time_ms: float) -> float:
    if python_time_ms <= 0:
        return 0.0
    if dfa_time_ms <= 0:
        return float("inf")
    return python_time_ms / dfa_time_ms

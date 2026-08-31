"""Performance benchmarking module comparing LogScan DFA against Python re engine."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import time
from typing import Any

from core.hopcroft import minimize_dfa
from core.regex_parser import RegexParser
from core.scanner import DFAScanner
from core.subset import nfa_to_dfa
from core.thompson import regex_to_nfa


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


@dataclass
class BenchmarkSuiteResult:
    pattern: str
    metrics: list[BenchmarkMetrics] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """Benchmark harness comparing DFA scanner performance vs standard python `re`."""

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.parser = RegexParser(pattern)
        self.ast = self.parser.parse()
        self.nfa = regex_to_nfa(pattern)
        self.dfa = nfa_to_dfa(self.nfa)
        self.minimal_dfa = minimize_dfa(self.dfa)
        self.scanner = DFAScanner(self.minimal_dfa)

    def run_single(self, text: str, label: str = "") -> BenchmarkMetrics:
        """Execute performance test on a single text payload."""
        text_bytes = len(text.encode("utf-8"))
        if not label:
            if text_bytes < 1024:
                label = f"{text_bytes} B"
            elif text_bytes < 1024 * 1024:
                label = f"{text_bytes / 1024:.1f} KB"
            else:
                label = f"{text_bytes / (1024 * 1024):.1f} MB"

        try:
            py_pattern = re.compile(self.pattern)
        except re.error:
            py_pattern = re.compile(re.escape(self.pattern))

        # Warmup execution
        _ = list(py_pattern.finditer(text))
        _ = self.scanner.find_matches(text)

        # Timed Python re pass
        start_py = time.perf_counter()
        py_matches = list(py_pattern.finditer(text))
        end_py = time.perf_counter()
        py_time_ms = (end_py - start_py) * 1000.0

        # Timed DFA Scanner pass
        start_dfa = time.perf_counter()
        dfa_matches = self.scanner.find_matches(text)
        end_dfa = time.perf_counter()
        dfa_time_ms = (end_dfa - start_dfa) * 1000.0

        speedup = py_time_ms / dfa_time_ms if dfa_time_ms > 0 else 1.0

        return BenchmarkMetrics(
            pattern=self.pattern,
            input_size_bytes=text_bytes,
            input_size_label=label,
            python_re_time_ms=round(py_time_ms, 3),
            python_re_matches=len(py_matches),
            dfa_scanner_time_ms=round(dfa_time_ms, 3),
            dfa_scanner_matches=len(dfa_matches),
            nfa_states=len(self.nfa.states),
            dfa_states=len(self.dfa.states),
            minimal_dfa_states=len(self.minimal_dfa.states),
            speedup_ratio=round(speedup, 2),
        )

    def run_scaling_benchmark(
        self,
        base_text: str,
        scales: list[int] | None = None,
    ) -> BenchmarkSuiteResult:
        """Run benchmark over increasing input sizes by repeating base_text."""
        if scales is None:
            scales = [1, 10, 50, 200, 1000]

        metrics_list = []
        for scale in scales:
            scaled_text = (base_text + "\n") * scale
            m = self.run_single(scaled_text)
            metrics_list.append(m)

        state_reduction = (
            round((1 - len(self.minimal_dfa.states) / len(self.dfa.states)) * 100, 1)
            if len(self.dfa.states) > 0
            else 0.0
        )

        summary = {
            "pattern": self.pattern,
            "nfa_states": len(self.nfa.states),
            "dfa_states": len(self.dfa.states),
            "minimal_dfa_states": len(self.minimal_dfa.states),
            "state_reduction_pct": state_reduction,
        }
        return BenchmarkSuiteResult(pattern=self.pattern, metrics=metrics_list, summary=summary)


def run_benchmark(pattern: str, text: str) -> BenchmarkMetrics:
    """Convenience helper to run a single benchmark."""
    return BenchmarkRunner(pattern).run_single(text)

import pytest

from benchmark.benchmark_runner import BenchmarkRunner, run_benchmark
from core.hopcroft import minimize_dfa
from core.regex_parser import RegexParser, RegexSyntaxError
from core.scanner import DFAScanner
from core.subset import DFA, SubsetConstructor, nfa_to_dfa
from core.thompson import regex_to_nfa
from visualization.graph_visualizer import visualize_dfa, visualize_nfa


def build_scanner(pattern: str) -> DFAScanner:
    nfa = regex_to_nfa(pattern)
    dfa = nfa_to_dfa(nfa)
    minimal = minimize_dfa(dfa)
    return DFAScanner(minimal)


def test_parser_builds_concat_union_ast():
    ast = RegexParser("ab|c*").parse()

    assert ast.node_type == "UNION"
    assert ast.left.node_type == "CONCAT"
    assert ast.left.left.value == "a"
    assert ast.left.right.value == "b"
    assert ast.right.node_type == "STAR"
    assert ast.right.left.value == "c"


def test_parser_expands_character_ranges_and_escapes():
    ast = RegexParser(r"[a-c]\.").parse()

    assert ast.node_type == "CONCAT"
    assert ast.left.node_type == "CHAR_CLASS"
    assert ast.left.value == {"a", "b", "c"}
    assert ast.right.node_type == "SYMBOL"
    assert ast.right.value == "."


def test_parser_rejects_invalid_syntax():
    with pytest.raises(RegexSyntaxError):
        RegexParser("(ab").parse()

    with pytest.raises(RegexSyntaxError):
        RegexParser("[z-a]").parse()


def test_thompson_creates_nfa_shape():
    nfa = regex_to_nfa("ab")

    assert nfa.start in nfa.states
    assert nfa.accept in nfa.states
    assert nfa.alphabet == {"a", "b"}
    assert any("a" in transitions for transitions in nfa.transitions.values())
    assert any(targets for targets in nfa.epsilon.values())


def test_subset_epsilon_closure_contains_star_accept():
    nfa = regex_to_nfa("a*")
    subset = SubsetConstructor(nfa)

    closure = subset.epsilon_closure({nfa.start})

    assert nfa.start in closure
    assert nfa.accept in closure


def test_dfa_scanner_accepts_and_rejects_full_strings():
    scanner = build_scanner("a(b|c)*")

    assert scanner.matches("a")
    assert scanner.matches("abcbcc")
    assert not scanner.matches("")
    assert not scanner.matches("b")
    assert not scanner.matches("acbd")


def test_optional_and_plus_operators():
    optional = build_scanner("a?")
    digits = build_scanner(r"\d+")

    assert optional.matches("")
    assert optional.matches("a")
    assert not optional.matches("aa")
    assert digits.matches("12345")
    assert not digits.matches("")
    assert not digits.matches("12a")


def test_wildcard_subset_transition_preserves_nfa_choices():
    scanner = build_scanner(".b|ab")

    assert scanner.matches("ab")
    assert scanner.matches("xb")
    assert not scanner.matches("ac")


def test_hopcroft_merges_equivalent_states():
    dfa = DFA(
        states={0, 1, 2},
        alphabet={"a", "b"},
        transitions={
            0: {"a": 1, "b": 2},
            1: {"a": 1, "b": 1},
            2: {"a": 1, "b": 1},
        },
        start=0,
        accepts={1, 2},
    )

    minimal = minimize_dfa(dfa)
    scanner = DFAScanner(minimal)

    assert len(minimal.states) == 2
    assert scanner.matches("a")
    assert scanner.matches("b")
    assert scanner.matches("aa")
    assert not scanner.matches("")


def test_scanner_finds_overlapping_matches():
    scanner = build_scanner("aba")

    assert scanner.find_matches("ababa") == [(0, 3), (2, 5)]


def test_scanner_can_return_non_overlapping_longest_matches():
    scanner = build_scanner("[0-9]+")

    assert scanner.find_matches("abc 12 345", overlapping=False) == [(4, 6), (7, 10)]


def test_visualization_nfa_and_dfa_returns_digraph():
    nfa = regex_to_nfa("a|b")
    dfa = minimize_dfa(nfa_to_dfa(nfa))

    nfa_dot = visualize_nfa(nfa)
    dfa_dot = visualize_dfa(dfa)

    assert nfa_dot is not None
    assert dfa_dot is not None
    assert "a" in nfa_dot.source
    assert "b" in dfa_dot.source


def test_benchmark_runner_single_and_scaling():
    metrics = run_benchmark("ERROR|WARN", "ERROR sample log line\nWARN memory high")

    assert metrics.pattern == "ERROR|WARN"
    assert metrics.dfa_scanner_matches == 2
    assert metrics.nfa_states > 0
    assert metrics.dfa_states > 0
    assert metrics.minimal_dfa_states > 0

    suite = BenchmarkRunner("ERROR").run_scaling_benchmark("INFO ok\nERROR failed", scales=[1, 2])
    assert len(suite.metrics) == 2
    assert suite.summary["pattern"] == "ERROR"


def test_multiline_wildcard_scanner():
    scanner = build_scanner("(ERROR|WARN).*")
    text = "2026-08-18 [INFO] OK\n2026-08-18 [WARN] Low disk space\n2026-08-18 [ERROR] Failure"
    matches = scanner.find_matches(text, overlapping=False, longest=True)

    assert len(matches) == 2
    assert text[matches[0][0]:matches[0][1]] == "WARN] Low disk space"
    assert text[matches[1][0]:matches[1][1]] == "ERROR] Failure"


def test_fast_forward_scanner_matches_count_with_re():
    runner = BenchmarkRunner("(ERROR|WARN).*")
    suite = runner.run_scaling_benchmark("", scales=[1, 5])

    for metric in suite.metrics:
        assert metric.dfa_scanner_matches == metric.python_re_matches


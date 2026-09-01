"""DOT visualization helpers for NFA and DFA automata.

The functions return Graphviz DOT strings. Streamlit can render those directly
with st.graphviz_chart, so the app does not require the Python graphviz package
at import time.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from core.subset import DFA
from core.thompson import ANY_SYMBOL, NFA


class DotGraph(str):
    """DOT string that also exposes a graphviz-like .source attribute."""

    @property
    def source(self) -> str:
        return str(self)


class AutomataVisualizer:
    """Render automata as Graphviz DOT diagrams."""

    @staticmethod
    def visualize_nfa(nfa: NFA, title: str = "Thompson epsilon-NFA") -> str:
        lines = _dot_header(title)
        lines.append(_node("__start", label="", shape="point", style="invis"))

        if nfa.start != -1:
            lines.append(_edge("__start", f"q{nfa.start}", "start"))

        for state in sorted(nfa.states):
            attrs = {"label": f"q{state}"}
            if state == nfa.accept:
                attrs.update({"shape": "doublecircle", "style": "bold", "color": "#2E7D32"})
            elif state == nfa.start:
                attrs.update({"shape": "circle", "style": "bold", "color": "#1565C0"})
            else:
                attrs.update({"shape": "circle"})
            lines.append(_node(f"q{state}", **attrs))

        edge_labels: dict[tuple[int, int], list[str]] = defaultdict(list)
        for source, symbol_map in nfa.transitions.items():
            for symbol, targets in symbol_map.items():
                for target in targets:
                    edge_labels[(source, target)].append(symbol)

        for source, targets in nfa.epsilon.items():
            for target in targets:
                edge_labels[(source, target)].append("epsilon")

        for (source, target), symbols in sorted(edge_labels.items()):
            lines.append(_edge(f"q{source}", f"q{target}", _compact_symbols(symbols)))

        lines.append("}")
        return DotGraph("\n".join(lines))

    @staticmethod
    def visualize_dfa(dfa: DFA, title: str = "DFA") -> str:
        lines = _dot_header(title)
        lines.append(_node("__start", label="", shape="point", style="invis"))

        if dfa.start is not None:
            lines.append(_edge("__start", f"q{dfa.start}", "start"))

        for state in sorted(dfa.states):
            attrs = {"label": _dfa_state_label(dfa, state)}
            if state in dfa.accepts:
                attrs.update({"shape": "doublecircle", "style": "bold", "color": "#2E7D32"})
            else:
                attrs.update({"shape": "circle"})
            if state == dfa.start:
                attrs["style"] = "bold"
                attrs["color"] = "#1565C0"
            lines.append(_node(f"q{state}", **attrs))

        edge_labels: dict[tuple[int, int], list[str]] = defaultdict(list)
        for source, symbol_map in dfa.transitions.items():
            for symbol, target in symbol_map.items():
                edge_labels[(source, target)].append(symbol)

        for (source, target), symbols in sorted(edge_labels.items()):
            lines.append(_edge(f"q{source}", f"q{target}", _compact_symbols(symbols)))

        lines.append("}")
        return DotGraph("\n".join(lines))


def visualize_nfa(nfa: NFA, title: str = "Thompson epsilon-NFA") -> str:
    return AutomataVisualizer.visualize_nfa(nfa, title)


def visualize_dfa(dfa: DFA, title: str = "DFA") -> str:
    return AutomataVisualizer.visualize_dfa(dfa, title)


def _dot_header(title: str) -> list[str]:
    return [
        f"digraph {_quote_id(title)} {{",
        "  rankdir=LR;",
        f"  graph [label={_quote_label(title)}, labelloc=t, fontsize=16];",
        '  node [shape=circle, fontname="Arial"];',
        '  edge [fontname="Arial"];',
    ]


def _node(identifier: str, **attrs: str) -> str:
    return f"  {_quote_id(identifier)} [{_attrs(attrs)}];"


def _edge(source: str, target: str, label: str) -> str:
    return f"  {_quote_id(source)} -> {_quote_id(target)} [label={_quote_label(label)}];"


def _attrs(attrs: dict[str, str]) -> str:
    return ", ".join(f"{key}={_quote_label(value)}" for key, value in attrs.items())


def _quote_id(value: str) -> str:
    return _quote_label(value)


def _quote_label(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _dfa_state_label(dfa: DFA, state: int) -> str:
    if state not in dfa.state_subsets:
        return f"q{state}"
    return f"q{state}\n{_format_state_set(dfa.state_subsets[state])}"


def _format_state_set(states: Iterable[int], limit: int = 12) -> str:
    ordered = sorted(states)
    visible = ordered[:limit]
    suffix = ",..." if len(ordered) > limit else ""
    return "{" + ",".join(str(state) for state in visible) + suffix + "}"


def _compact_symbols(symbols: Iterable[str]) -> str:
    unique = set(symbols)
    labels: list[str] = []

    if "epsilon" in unique:
        labels.append("epsilon")
        unique.remove("epsilon")
    if ANY_SYMBOL in unique:
        labels.append(".")
        unique.remove(ANY_SYMBOL)

    single_chars = sorted((symbol for symbol in unique if len(symbol) == 1), key=ord)
    labels.extend(_range_labels(single_chars))

    labels.extend(
        _format_symbol(symbol)
        for symbol in sorted(unique)
        if len(symbol) != 1
    )

    return ", ".join(labels)


def _range_labels(chars: list[str]) -> list[str]:
    if not chars:
        return []

    labels: list[str] = []
    start = chars[0]
    previous = chars[0]

    for char in chars[1:]:
        if ord(char) == ord(previous) + 1:
            previous = char
            continue
        labels.extend(_format_range(start, previous))
        start = previous = char

    labels.extend(_format_range(start, previous))
    return labels


def _format_range(start: str, end: str) -> list[str]:
    if start == end:
        return [_format_symbol(start)]
    if ord(end) == ord(start) + 1:
        return [_format_symbol(start), _format_symbol(end)]
    return [f"{_format_symbol(start)}-{_format_symbol(end)}"]


def _format_symbol(symbol: str) -> str:
    return {
        "\n": r"\n",
        "\r": r"\r",
        "\t": r"\t",
        " ": "space",
    }.get(symbol, symbol)

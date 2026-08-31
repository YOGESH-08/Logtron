"""Graphviz visualization engine for NFA and DFA automata."""

from __future__ import annotations

import graphviz

from core.subset import DFA
from core.thompson import ANY_SYMBOL, NFA


class AutomataVisualizer:
    """Renders Graphviz state diagrams for NFAs and DFAs."""

    @staticmethod
    def visualize_nfa(nfa: NFA, title: str = "Thompson ε-NFA") -> graphviz.Digraph:
        """Create a Graphviz Digraph representing an epsilon-NFA."""
        dot = graphviz.Digraph(name=title, comment=title)
        dot.attr(rankdir="LR", size="8,5")
        dot.attr("node", shape="circle")
        dot.attr(label=title, labelloc="t", fontsize="16")

        # Invisible start arrow
        dot.node("start_nfa", style="invis", shape="point")
        if nfa.start != -1:
            dot.edge("start_nfa", str(nfa.start), label="start")

        # Nodes
        for state in sorted(nfa.states):
            if state == nfa.accept:
                dot.node(str(state), shape="doublecircle", style="bold", color="#2E7D32")
            elif state == nfa.start:
                dot.node(str(state), shape="circle", style="bold", color="#1565C0")
            else:
                dot.node(str(state), shape="circle")

        # Symbol transitions
        for source, symbol_map in nfa.transitions.items():
            for symbol, targets in symbol_map.items():
                label = "." if symbol == ANY_SYMBOL else symbol
                for target in sorted(targets):
                    dot.edge(str(source), str(target), label=label)

        # Epsilon transitions
        for source, targets in nfa.epsilon.items():
            for target in sorted(targets):
                dot.edge(str(source), str(target), label="ε", style="dashed", color="#666666")

        return dot

    @staticmethod
    def visualize_dfa(dfa: DFA, title: str = "DFA") -> graphviz.Digraph:
        """Create a Graphviz Digraph representing a DFA or Minimal DFA."""
        dot = graphviz.Digraph(name=title, comment=title)
        dot.attr(rankdir="LR", size="8,5")
        dot.attr("node", shape="circle")
        dot.attr(label=title, labelloc="t", fontsize="16")

        # Invisible start arrow
        dot.node("start_dfa", style="invis", shape="point")
        if dfa.start is not None:
            dot.edge("start_dfa", str(dfa.start), label="start")

        # Group transitions between the same (source, target) pair
        edge_labels: dict[tuple[int, int], list[str]] = {}

        for source, symbol_map in dfa.transitions.items():
            for symbol, target in symbol_map.items():
                label = "." if symbol == ANY_SYMBOL else symbol
                edge_labels.setdefault((source, target), []).append(label)

        # Nodes
        for state in sorted(dfa.states):
            label = str(state)
            if state in dfa.state_subsets:
                subset_str = "{" + ",".join(map(str, sorted(dfa.state_subsets[state]))) + "}"
                label = f"{state}\n{subset_str}"

            if state in dfa.accepts and state == dfa.start:
                dot.node(str(state), label=label, shape="doublecircle", style="bold", color="#1565C0")
            elif state in dfa.accepts:
                dot.node(str(state), label=label, shape="doublecircle", style="bold", color="#2E7D32")
            elif state == dfa.start:
                dot.node(str(state), label=label, shape="circle", style="bold", color="#1565C0")
            else:
                dot.node(str(state), label=label, shape="circle")

        # Edges
        for (source, target), labels in edge_labels.items():
            combined_label = ", ".join(sorted(labels))
            dot.edge(str(source), str(target), label=combined_label)

        return dot


def visualize_nfa(nfa: NFA, title: str = "Thompson ε-NFA") -> graphviz.Digraph:
    """Convenience helper to render NFA to Digraph."""
    return AutomataVisualizer.visualize_nfa(nfa, title)


def visualize_dfa(dfa: DFA, title: str = "DFA") -> graphviz.Digraph:
    """Convenience helper to render DFA to Digraph."""
    return AutomataVisualizer.visualize_dfa(dfa, title)

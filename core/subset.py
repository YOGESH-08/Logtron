"""Subset construction for converting epsilon-NFAs to DFAs."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

from core.thompson import ANY_SYMBOL, NFA


@dataclass
class DFA:
    states: set[int] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)
    transitions: dict[int, dict[str, int]] = field(default_factory=dict)
    start: int | None = None
    accepts: set[int] = field(default_factory=set)
    state_subsets: dict[int, frozenset[int]] = field(default_factory=dict)

    def add_state(self, state: int) -> None:
        self.states.add(state)
        self.transitions.setdefault(state, {})

    def add_transition(self, source: int, symbol: str, target: int) -> None:
        self.add_state(source)
        self.add_state(target)
        self.alphabet.add(symbol)
        self.transitions[source][symbol] = target


class SubsetConstructor:
    """Convert an epsilon-NFA into a DFA using powerset construction."""

    def __init__(self, nfa: NFA):
        self.nfa = nfa

    def epsilon_closure(self, states: Iterable[int]) -> set[int]:
        """Return states reachable through zero or more epsilon transitions."""
        closure = set(states)
        stack = list(closure)

        while stack:
            state = stack.pop()
            for target in self.nfa.epsilon.get(state, set()):
                if target not in closure:
                    closure.add(target)
                    stack.append(target)

        return closure

    def move(self, states: Iterable[int], symbol: str) -> set[int]:
        """Return NFA states reachable by consuming symbol from any state.

        For concrete symbols, wildcard transitions are included because a dot in
        the source regex can consume any actual input character.
        """
        reachable: set[int] = set()

        for state in states:
            transitions = self.nfa.transitions.get(state, {})
            reachable.update(transitions.get(symbol, set()))
            if symbol != ANY_SYMBOL:
                reachable.update(transitions.get(ANY_SYMBOL, set()))

        return reachable

    def convert(self) -> DFA:
        """Build and return a DFA equivalent to the configured NFA."""
        if self.nfa.start == -1 or self.nfa.accept == -1:
            raise ValueError("NFA must have valid start and accept states")

        dfa = DFA(alphabet=set(self.nfa.alphabet))
        start_subset = frozenset(self.epsilon_closure({self.nfa.start}))
        subset_to_state: dict[frozenset[int], int] = {start_subset: 0}
        queue: deque[frozenset[int]] = deque([start_subset])

        dfa.start = 0
        dfa.add_state(0)
        dfa.state_subsets[0] = start_subset
        if self.nfa.accept in start_subset:
            dfa.accepts.add(0)

        while queue:
            current_subset = queue.popleft()
            current_state = subset_to_state[current_subset]

            for symbol in sorted(self.nfa.alphabet):
                moved = self.move(current_subset, symbol)
                if not moved:
                    continue

                target_subset = frozenset(self.epsilon_closure(moved))
                if not target_subset:
                    continue

                if target_subset not in subset_to_state:
                    new_state = len(subset_to_state)
                    subset_to_state[target_subset] = new_state
                    dfa.add_state(new_state)
                    dfa.state_subsets[new_state] = target_subset
                    if self.nfa.accept in target_subset:
                        dfa.accepts.add(new_state)
                    queue.append(target_subset)

                dfa.add_transition(current_state, symbol, subset_to_state[target_subset])

        return dfa


def nfa_to_dfa(nfa: NFA) -> DFA:
    """Convenience wrapper for SubsetConstructor(nfa).convert()."""
    return SubsetConstructor(nfa).convert()

"""
Thompson Construction

Converts a regular-expression AST into an epsilon-NFA.

Supported AST nodes:
    SYMBOL
    ANY
    CHAR_CLASS
    CONCAT
    UNION
    STAR
    PLUS
    OPTIONAL
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, Optional

from .regex_parser import ASTNode


# ============================================================
# NFA
# ============================================================

@dataclass
class NFA:
    """
    Represents a nondeterministic finite automaton.
    """

    states: Set[int] = field(default_factory=set)

    alphabet: Set[str] = field(default_factory=set)

    transitions: Dict[
        int,
        Dict[str, Set[int]]
    ] = field(default_factory=dict)

    epsilon: Dict[
        int,
        Set[int]
    ] = field(default_factory=dict)

    start: int = -1

    accept: int = -1

    def add_state(self, state: int):
        """Add a state to the NFA."""

        self.states.add(state)

        if state not in self.transitions:
            self.transitions[state] = {}

        if state not in self.epsilon:
            self.epsilon[state] = set()

    def add_transition(
        self,
        source: int,
        symbol: str,
        destination: int
    ):
        """Add a normal symbol transition."""

        self.add_state(source)
        self.add_state(destination)

        if symbol not in self.transitions[source]:
            self.transitions[source][symbol] = set()

        self.transitions[source][symbol].add(destination)

        self.alphabet.add(symbol)

    def add_epsilon(
        self,
        source: int,
        destination: int
    ):
        """Add an epsilon transition."""

        self.add_state(source)
        self.add_state(destination)

        self.epsilon[source].add(destination)


# ============================================================
# THOMPSON FRAGMENT
# ============================================================

@dataclass
class Fragment:
    """
    A partial NFA produced during Thompson construction.

    Every fragment has:

        start
        accept

    Example:

        start ----a----> accept
    """

    start: int
    accept: int

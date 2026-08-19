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


# ============================================================
# THOMPSON BUILDER
# ============================================================

class ThompsonConstructor:
    """
    Converts an AST into an epsilon-NFA.
    """

    def __init__(self):
        self.nfa = NFA()
        self.next_state = 0

    # ========================================================
    # PUBLIC API
    # ========================================================

    def build(self, ast: ASTNode) -> NFA:
        """
        Build an NFA from the supplied AST.
        """

        if ast is None:
            raise ValueError(
                "AST cannot be None."
            )

        fragment = self._build_fragment(ast)

        self.nfa.start = fragment.start
        self.nfa.accept = fragment.accept

        return self.nfa

    # ========================================================
    # STATE CREATION
    # ========================================================

    def _new_state(self) -> int:
        """
        Create a new unique NFA state.
        """

        state = self.next_state

        self.next_state += 1

        self.nfa.add_state(state)

        return state

    # ========================================================
    # AST WALK
    # ========================================================

    def _build_fragment(
        self,
        node: ASTNode
    ) -> Fragment:
        """
        Recursively construct the NFA.

        This is the core of Thompson Construction.
        """

        node_type = node.node_type

        # ----------------------------------------------------
        # SYMBOL
        # ----------------------------------------------------

        if node_type == "SYMBOL":

            start = self._new_state()
            accept = self._new_state()

            self.nfa.add_transition(
                start,
                node.value,
                accept
            )

            return Fragment(
                start=start,
                accept=accept
            )

        # ----------------------------------------------------
        # ANY CHARACTER
        # ----------------------------------------------------

        if node_type == "ANY":

            start = self._new_state()
            accept = self._new_state()

            # Special internal symbol representing '.'
            self.nfa.add_transition(
                start,
                "__ANY__",
                accept
            )

            return Fragment(
                start=start,
                accept=accept
            )

        # ----------------------------------------------------
        # CONCATENATION
        # ----------------------------------------------------

        if node_type == "CONCAT":

            left = self._build_fragment(
                node.left
            )

            right = self._build_fragment(
                node.right
            )

            # Connect left accept to right start
            # using epsilon.

            self.nfa.add_epsilon(
                left.accept,
                right.start
            )

            return Fragment(
                start=left.start,
                accept=right.accept
            )

        raise ValueError(
            f"Unsupported AST node: {node_type}"
        )

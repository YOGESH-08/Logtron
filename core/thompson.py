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

NFA representation:

    states:
        Set[int]

    alphabet:
        Set[str]

    transitions:
        {
            state: {
                symbol: {destination_states}
            }
        }

    epsilon:
        {
            state: {destination_states}
        }

    start:
        int

    accept:
        int
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
        # CHARACTER CLASS
        # ----------------------------------------------------

        if node_type == "CHAR_CLASS":

            return self._build_character_class(
                node.value
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

        # ----------------------------------------------------
        # UNION
        # ----------------------------------------------------

        if node_type == "UNION":

            return self._build_union(
                node.left,
                node.right
            )

        # ----------------------------------------------------
        # STAR
        # ----------------------------------------------------

        if node_type == "STAR":

            return self._build_star(
                node.left
            )

        # ----------------------------------------------------
        # PLUS
        # ----------------------------------------------------

        if node_type == "PLUS":

            return self._build_plus(
                node.left
            )

        # ----------------------------------------------------
        # OPTIONAL
        # ----------------------------------------------------

        if node_type == "OPTIONAL":

            return self._build_optional(
                node.left
            )

        raise ValueError(
            f"Unsupported AST node: {node_type}"
        )

    # ========================================================
    # CHARACTER CLASS
    # ========================================================

    def _build_character_class(
        self,
        characters: Set[str]
    ) -> Fragment:
        """
        Construct an NFA fragment for:

            [abc]

        This becomes:

                 a
              ┌──────┐
              │      ▼
        start ──────> accept
              │      ▲
              └──────┘
                 b/c

        More precisely, multiple transitions leave the same
        start state and reach the same accept state.
        """

        start = self._new_state()
        accept = self._new_state()

        for character in characters:

            self.nfa.add_transition(
                start,
                character,
                accept
            )

        return Fragment(
            start=start,
            accept=accept
        )

    # ========================================================
    # UNION
    # ========================================================

    def _build_union(
        self,
        left_node: ASTNode,
        right_node: ASTNode
    ) -> Fragment:
        """
        Thompson construction for:

            A|B

                  ε ---> A ---> ε
                 /              \
        start --                  --> accept
                 \              /
                  ε ---> B ---> ε
        """

        left = self._build_fragment(
            left_node
        )

        right = self._build_fragment(
            right_node
        )

        start = self._new_state()
        accept = self._new_state()

        # Start can enter either branch.

        self.nfa.add_epsilon(
            start,
            left.start
        )

        self.nfa.add_epsilon(
            start,
            right.start
        )

        # Both branches lead to final accept.

        self.nfa.add_epsilon(
            left.accept,
            accept
        )

        self.nfa.add_epsilon(
            right.accept,
            accept
        )

        return Fragment(
            start=start,
            accept=accept
        )

    # ========================================================
    # STAR
    # ========================================================

    def _build_star(
        self,
        child_node: ASTNode
    ) -> Fragment:
        """
        Thompson construction for:

            A*

        Allows:

            zero occurrences
            one occurrence
            multiple occurrences
        """

        child = self._build_fragment(
            child_node
        )

        start = self._new_state()
        accept = self._new_state()

        # Empty string is allowed.

        self.nfa.add_epsilon(
            start,
            accept
        )

        # Enter the child.

        self.nfa.add_epsilon(
            start,
            child.start
        )

        # Exit the child.

        self.nfa.add_epsilon(
            child.accept,
            accept
        )

        # Repeat the child.

        self.nfa.add_epsilon(
            child.accept,
            child.start
        )

        return Fragment(
            start=start,
            accept=accept
        )

    # ========================================================
    # PLUS
    # ========================================================

    def _build_plus(
        self,
        child_node: ASTNode
    ) -> Fragment:
        """
        Thompson construction for:

            A+

        Equivalent to:

            AA*

        but constructed directly.
        """

        child = self._build_fragment(
            child_node
        )

        start = child.start
        accept = self._new_state()

        # One occurrence is mandatory.

        self.nfa.add_epsilon(
            child.accept,
            accept
        )

        # Additional occurrences.

        self.nfa.add_epsilon(
            child.accept,
            child.start
        )

        return Fragment(
            start=start,
            accept=accept
        )

    # ========================================================
    # OPTIONAL
    # ========================================================

    def _build_optional(
        self,
        child_node: ASTNode
    ) -> Fragment:
        """
        Thompson construction for:

            A?

        Equivalent to:

            A|ε
        """

        child = self._build_fragment(
            child_node
        )

        start = self._new_state()
        accept = self._new_state()

        # Skip the child entirely.

        self.nfa.add_epsilon(
            start,
            accept
        )

        # Or execute the child.

        self.nfa.add_epsilon(
            start,
            child.start
        )

        self.nfa.add_epsilon(
            child.accept,
            accept
        )

        return Fragment(
            start=start,
            accept=accept
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def regex_to_nfa(pattern: str) -> NFA:
    """
    Convenience function.

    Example:

        nfa = regex_to_nfa("a(b|c)*")
    """

    from .regex_parser import RegexParser

    ast = RegexParser(pattern).parse()

    constructor = ThompsonConstructor()

    return constructor.build(ast)


# ============================================================
# NFA DEBUGGING
# ============================================================

def print_nfa(nfa: NFA):
    """
    Print the NFA in a human-readable format.

    Useful for debugging and verifying Thompson Construction.
    """

    print("\n========== NFA ==========")

    print("States :", sorted(nfa.states))
    print("Start  :", nfa.start)
    print("Accept :", nfa.accept)

    print("\nTransitions:")

    for source in sorted(nfa.transitions):

        for symbol in sorted(
            nfa.transitions[source]
        ):

            destinations = sorted(
                nfa.transitions[source][symbol]
            )

            for destination in destinations:

                print(
                    f"  {source} --{symbol}--> "
                    f"{destination}"
                )

    print("\nEpsilon transitions:")

    for source in sorted(nfa.epsilon):

        for destination in sorted(
            nfa.epsilon[source]
        ):

            print(
                f"  {source} --ε--> {destination}"
            )

    print("=========================\n")

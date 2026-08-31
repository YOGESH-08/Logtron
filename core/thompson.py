"""Thompson construction from regex ASTs to epsilon-NFAs."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.regex_parser import ASTNode, RegexParser


ANY_SYMBOL = "__ANY__"


@dataclass
class NFA:
    states: set[int] = field(default_factory=set)
    alphabet: set[str] = field(default_factory=set)
    transitions: dict[int, dict[str, set[int]]] = field(default_factory=dict)
    epsilon: dict[int, set[int]] = field(default_factory=dict)
    start: int = -1
    accept: int = -1

    def add_state(self, state: int) -> None:
        self.states.add(state)
        self.transitions.setdefault(state, {})
        self.epsilon.setdefault(state, set())

    def add_transition(self, source: int, symbol: str, target: int) -> None:
        self.add_state(source)
        self.add_state(target)
        self.alphabet.add(symbol)
        self.transitions[source].setdefault(symbol, set()).add(target)

    def add_epsilon(self, source: int, target: int) -> None:
        self.add_state(source)
        self.add_state(target)
        self.epsilon[source].add(target)


@dataclass(frozen=True)
class NFAFragment:
    start: int
    accept: int


class ThompsonConstructor:
    """Build an epsilon-NFA from an AST using Thompson's construction."""

    def __init__(self):
        self._next_state = 0
        self.nfa = NFA()

    def build(self, ast: ASTNode | None) -> NFA:
        if ast is None:
            raise ValueError("AST cannot be None")

        fragment = self._build_fragment(ast)
        self.nfa.start = fragment.start
        self.nfa.accept = fragment.accept
        return self.nfa

    def _new_state(self) -> int:
        state = self._next_state
        self._next_state += 1
        self.nfa.add_state(state)
        return state

    def _build_fragment(self, node: ASTNode) -> NFAFragment:
        if node.node_type == "SYMBOL":
            return self._symbol_fragment(node.value)
        if node.node_type == "ANY":
            return self._symbol_fragment(ANY_SYMBOL)
        if node.node_type == "CHAR_CLASS":
            return self._character_class_fragment(set(node.value))
        if node.node_type == "CONCAT":
            return self._concat_fragment(node)
        if node.node_type == "UNION":
            return self._union_fragment(node)
        if node.node_type == "STAR":
            return self._star_fragment(node)
        if node.node_type == "PLUS":
            return self._plus_fragment(node)
        if node.node_type == "OPTIONAL":
            return self._optional_fragment(node)

        raise ValueError(f"unsupported AST node type: {node.node_type!r}")

    def _symbol_fragment(self, symbol: str) -> NFAFragment:
        start = self._new_state()
        accept = self._new_state()
        self.nfa.add_transition(start, symbol, accept)
        return NFAFragment(start, accept)

    def _character_class_fragment(self, characters: set[str]) -> NFAFragment:
        if not characters:
            raise ValueError("character class cannot be empty")

        start = self._new_state()
        accept = self._new_state()
        for character in characters:
            self.nfa.add_transition(start, character, accept)
        return NFAFragment(start, accept)

    def _concat_fragment(self, node: ASTNode) -> NFAFragment:
        left = self._build_fragment(self._require_child(node.left, "CONCAT left"))
        right = self._build_fragment(self._require_child(node.right, "CONCAT right"))
        self.nfa.add_epsilon(left.accept, right.start)
        return NFAFragment(left.start, right.accept)

    def _union_fragment(self, node: ASTNode) -> NFAFragment:
        left = self._build_fragment(self._require_child(node.left, "UNION left"))
        right = self._build_fragment(self._require_child(node.right, "UNION right"))
        start = self._new_state()
        accept = self._new_state()

        self.nfa.add_epsilon(start, left.start)
        self.nfa.add_epsilon(start, right.start)
        self.nfa.add_epsilon(left.accept, accept)
        self.nfa.add_epsilon(right.accept, accept)
        return NFAFragment(start, accept)

    def _star_fragment(self, node: ASTNode) -> NFAFragment:
        child = self._build_fragment(self._require_child(node.left, "STAR child"))
        start = self._new_state()
        accept = self._new_state()

        self.nfa.add_epsilon(start, child.start)
        self.nfa.add_epsilon(start, accept)
        self.nfa.add_epsilon(child.accept, child.start)
        self.nfa.add_epsilon(child.accept, accept)
        return NFAFragment(start, accept)

    def _plus_fragment(self, node: ASTNode) -> NFAFragment:
        child = self._build_fragment(self._require_child(node.left, "PLUS child"))
        start = self._new_state()
        accept = self._new_state()

        self.nfa.add_epsilon(start, child.start)
        self.nfa.add_epsilon(child.accept, child.start)
        self.nfa.add_epsilon(child.accept, accept)
        return NFAFragment(start, accept)

    def _optional_fragment(self, node: ASTNode) -> NFAFragment:
        child = self._build_fragment(self._require_child(node.left, "OPTIONAL child"))
        start = self._new_state()
        accept = self._new_state()

        self.nfa.add_epsilon(start, child.start)
        self.nfa.add_epsilon(start, accept)
        self.nfa.add_epsilon(child.accept, accept)
        return NFAFragment(start, accept)

    def _require_child(self, child: ASTNode | None, label: str) -> ASTNode:
        if child is None:
            raise ValueError(f"{label} is missing")
        return child


def regex_to_nfa(pattern: str) -> NFA:
    ast = RegexParser(pattern).parse()
    return ThompsonConstructor().build(ast)

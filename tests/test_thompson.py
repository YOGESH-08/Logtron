"""
Unit tests for Thompson Construction NFA synthesis.
"""

import pytest
from core.thompson import regex_to_nfa, ThompsonConstructor, NFA
from core.regex_parser import ASTNode


def test_symbol_nfa():
    nfa = regex_to_nfa("a")
    assert len(nfa.states) == 2
    assert nfa.start in nfa.transitions
    assert "a" in nfa.transitions[nfa.start]
    assert nfa.accept in nfa.transitions[nfa.start]["a"]


def test_concat_nfa():
    nfa = regex_to_nfa("ab")
    assert nfa.start is not None
    assert nfa.accept is not None
    assert "a" in nfa.alphabet
    assert "b" in nfa.alphabet


def test_union_nfa():
    nfa = regex_to_nfa("a|b")
    assert nfa.start in nfa.epsilon
    assert len(nfa.epsilon[nfa.start]) == 2


def test_star_nfa():
    nfa = regex_to_nfa("a*")
    assert nfa.start in nfa.epsilon
    assert nfa.accept in nfa.states


def test_plus_nfa():
    nfa = regex_to_nfa("a+")
    assert nfa.start is not None
    assert nfa.accept in nfa.states


def test_optional_nfa():
    nfa = regex_to_nfa("a?")
    assert nfa.start in nfa.epsilon
    assert nfa.accept in nfa.epsilon[nfa.start]


def test_char_class_nfa():
    nfa = regex_to_nfa("[abc]")
    assert nfa.start in nfa.transitions
    assert "a" in nfa.transitions[nfa.start]
    assert "b" in nfa.transitions[nfa.start]
    assert "c" in nfa.transitions[nfa.start]


def test_invalid_ast_raises():
    constructor = ThompsonConstructor()
    with pytest.raises(ValueError):
        constructor.build(None)

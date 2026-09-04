"""DFA scanner engine for full matches and substring search."""

import re
from dataclasses import dataclass

from core.subset import DFA
from core.thompson import ANY_SYMBOL


@dataclass(frozen=True)
class Match:
    start: int
    end: int
    text: str

    def as_span(self) -> tuple[int, int]:
        return (self.start, self.end)


class DFAScanner:
    """Run deterministic input through a DFA.

    Substring search uses pre-compiled transition tables and fast-forwarding to achieve
    high performance linear scanning across log files.
    """

    def __init__(self, dfa: DFA):
        if dfa.start is None:
            raise ValueError("DFA must have a start state")
        self.dfa = dfa
        self.start = dfa.start
        self.accepts = set(dfa.accepts)

        self._fast_trans = {
            state: (trans, trans.get(ANY_SYMBOL))
            for state, trans in dfa.transitions.items()
        }

        start_tr = dfa.transitions.get(self.start, {})
        self.start_has_any = ANY_SYMBOL in start_tr
        self.start_chars = tuple(sorted(set(start_tr.keys()) - {ANY_SYMBOL}))
        self.single_start_char = self.start_chars[0] if len(self.start_chars) == 1 else None

        if len(self.start_chars) > 5:
            pattern_str = "[" + "".join(re.escape(c) for c in self.start_chars) + "]"
            self.start_re = re.compile(pattern_str)
        else:
            self.start_re = None

    def matches(self, text: str) -> bool:
        """Return True when the complete input string is accepted."""
        state = self.start

        for character in text:
            state = self.next_state(state, character)
            if state is None:
                return False

        return state in self.accepts

    def find_matches(
        self,
        text: str,
        *,
        overlapping: bool = True,
        longest: bool = True,
    ) -> list[tuple[int, int]]:
        """Return accepted substring spans as half-open (start, end) offsets."""
        spans: list[tuple[int, int]] = []
        n = len(text)
        start = 0
        dfa_start = self.start
        accepts = self.accepts
        fast_trans = self._fast_trans
        start_has_any = self.start_has_any
        start_chars = self.start_chars
        single_start_char = self.single_start_char
        start_re = self.start_re

        while start < n:
            if not start_has_any:
                if single_start_char:
                    pos = text.find(single_start_char, start)
                    if pos == -1:
                        break
                    start = pos
                elif start_chars:
                    if start_re is not None:
                        m = start_re.search(text, start)
                        if not m:
                            break
                        start = m.start()
                    else:
                        min_pos = -1
                        for c in start_chars:
                            p = text.find(c, start)
                            if p != -1 and (min_pos == -1 or p < min_pos):
                                min_pos = p
                        if min_pos == -1:
                            break
                        start = min_pos

            state = dfa_start
            last_accept_end: int | None = None
            consumed_any = False
            curr = start

            while curr < n:
                char = text[curr]
                tr, any_tr = fast_trans.get(state, ({}, None))
                if char in tr:
                    state = tr[char]
                elif char != "\n":
                    state = any_tr
                else:
                    state = None

                if state is None:
                    break

                consumed_any = True
                curr += 1

                if state in accepts:
                    if longest:
                        last_accept_end = curr
                    else:
                        spans.append((start, curr))
                        if not overlapping:
                            start = curr - 1
                            break

            if longest and last_accept_end is not None:
                spans.append((start, last_accept_end))
                if not overlapping:
                    start = last_accept_end
                    continue

            start += 1 if consumed_any or overlapping else 1

        return spans

    def find_match_objects(
        self,
        text: str,
        *,
        overlapping: bool = True,
        longest: bool = True,
    ) -> list[Match]:
        """Return match objects with spans and matched text."""
        return [
            Match(start, end, text[start:end])
            for start, end in self.find_matches(text, overlapping=overlapping, longest=longest)
        ]

    def search(self, text: str) -> tuple[int, int] | None:
        """Return the first substring match, or None if no match exists."""
        matches = self.find_matches(text)
        return matches[0] if matches else None

    def next_state(self, state: int, character: str) -> int | None:
        """Advance from state by one input character."""
        tr, any_tr = self._fast_trans.get(state, ({}, None))
        if character in tr:
            return tr[character]
        if character != "\n":
            return any_tr
        return None


def scan(dfa: DFA, text: str) -> list[tuple[int, int]]:
    """Convenience wrapper for DFAScanner(dfa).find_matches(text)."""
    return DFAScanner(dfa).find_matches(text)

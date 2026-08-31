"""DFA scanner engine for full matches and substring search."""

from __future__ import annotations

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

    Substring search uses a simple per-position restart. It is deterministic and
    easy to explain, but it is not universally linear in the length of the log.
    """

    def __init__(self, dfa: DFA):
        if dfa.start is None:
            raise ValueError("DFA must have a start state")
        self.dfa = dfa

    def matches(self, text: str) -> bool:
        """Return True when the complete input string is accepted."""
        state = self.dfa.start

        for character in text:
            state = self.next_state(state, character)
            if state is None:
                return False

        return state in self.dfa.accepts

    def find_matches(
        self,
        text: str,
        *,
        overlapping: bool = True,
        longest: bool = True,
    ) -> list[tuple[int, int]]:
        """Return accepted substring spans as half-open (start, end) offsets.

        By default the scanner returns the longest match from every start
        position, so overlapping matches from different starts are preserved
        without reporting every accepted prefix of the same start position.
        """
        spans: list[tuple[int, int]] = []
        start = 0

        while start < len(text):
            state = self.dfa.start
            last_accept_end: int | None = None
            consumed_any = False

            for end in range(start, len(text)):
                state = self.next_state(state, text[end])
                if state is None:
                    break

                consumed_any = True
                if state in self.dfa.accepts:
                    accepted_end = end + 1
                    if longest:
                        last_accept_end = accepted_end
                    else:
                        spans.append((start, accepted_end))
                        if not overlapping:
                            start = accepted_end - 1
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
        transitions = self.dfa.transitions.get(state, {})
        if character in transitions:
            return transitions[character]
        return transitions.get(ANY_SYMBOL)


def scan(dfa: DFA, text: str) -> list[tuple[int, int]]:
    """Convenience wrapper for DFAScanner(dfa).find_matches(text)."""
    return DFAScanner(dfa).find_matches(text)

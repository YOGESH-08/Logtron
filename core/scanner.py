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

    Substring search uses pre-compiled transition tables, automatic literal prefix shortcuts,
    and fast-forwarding to achieve high performance linear scanning across log files.
    """

    def __init__(self, dfa: DFA):
        if dfa.start is None:
            raise ValueError("DFA must have a start state")
        self.dfa = dfa
        self.start = dfa.start
        self.accepts = set(dfa.accepts)

        max_state = max(dfa.states) if dfa.states else 0
        self._accept_flags = tuple(s in dfa.accepts for s in range(max_state + 1))
        self._self_loop_any_accepts = tuple(
            s in dfa.accepts and dfa.transitions.get(s, {}).get(ANY_SYMBOL) == s
            for s in range(max_state + 1)
        )

        self._fast_trans_list = [
            (dfa.transitions.get(s, {}), dfa.transitions.get(s, {}).get(ANY_SYMBOL))
            for s in range(max_state + 1)
        ]
        self._fast_trans = {
            state: (trans, trans.get(ANY_SYMBOL))
            for state, trans in dfa.transitions.items()
        }

        start_tr = dfa.transitions.get(self.start, {})
        self.start_has_any = ANY_SYMBOL in start_tr
        self.start_chars = tuple(sorted(set(start_tr.keys()) - {ANY_SYMBOL}))
        self.single_start_char = self.start_chars[0] if len(self.start_chars) == 1 else None

        if len(self.start_chars) > 1:
            pattern_str = "[" + "".join(re.escape(c) for c in self.start_chars) + "]"
            self.start_re = re.compile(pattern_str)
        else:
            self.start_re = None

        self._literal_prefixes = tuple(self._extract_literal_prefixes(dfa))

    def _extract_literal_prefixes(self, dfa: DFA) -> list[tuple[str, int, int]]:
        """Extract deterministic multi-character literal paths from the start state."""
        prefixes: list[tuple[str, int, int]] = []
        start_tr = dfa.transitions.get(dfa.start, {})
        if ANY_SYMBOL in start_tr:
            return []

        for symbol, target in start_tr.items():
            if len(symbol) != 1:
                continue
            chars = [symbol]
            curr = target

            while True:
                if curr in dfa.accepts:
                    break
                tr = dfa.transitions.get(curr, {})
                if len(tr) != 1 or ANY_SYMBOL in tr:
                    break
                next_char, next_target = list(tr.items())[0]
                if len(next_char) != 1:
                    break
                chars.append(next_char)
                curr = next_target

            literal = "".join(chars)
            if len(literal) > 1:
                prefixes.append((literal, curr, len(literal)))

        return prefixes

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
        dfa_start = self.start
        accept_flags = self._accept_flags
        self_loop_any_accepts = self._self_loop_any_accepts
        fast_trans_list = self._fast_trans_list
        start_has_any = self.start_has_any
        single_start_char = self.single_start_char
        start_re = self.start_re
        literal_prefixes = self._literal_prefixes

        # Accelerated finditer candidate matching for non-overlapping unanchored searches
        if not start_has_any and start_re is not None and not overlapping:
            last_end = 0
            for match_obj in start_re.finditer(text):
                start = match_obj.start()
                if start < last_end:
                    continue

                state = dfa_start
                last_accept_end: int | None = None
                curr = start

                for literal, target_state, lit_len in literal_prefixes:
                    if text.startswith(literal, curr):
                        curr += lit_len
                        state = target_state
                        if accept_flags[state]:
                            last_accept_end = curr
                        break

                while curr < n:
                    if self_loop_any_accepts[state]:
                        next_nl = text.find("\n", curr)
                        curr = n if next_nl == -1 else next_nl
                        last_accept_end = curr
                        break

                    char = text[curr]
                    tr, any_tr = fast_trans_list[state]
                    if char in tr:
                        state = tr[char]
                    elif char != "\n":
                        state = any_tr
                    else:
                        state = None

                    if state is None:
                        break

                    curr += 1
                    if accept_flags[state]:
                        if longest:
                            last_accept_end = curr

                if longest and last_accept_end is not None:
                    spans.append((start, last_accept_end))
                    last_end = last_accept_end

            return spans

        # General scanning fallback
        start = 0
        while start < n:
            if not start_has_any:
                if single_start_char:
                    pos = text.find(single_start_char, start)
                    if pos == -1:
                        break
                    start = pos
                elif start_re is not None:
                    m = start_re.search(text, start)
                    if not m:
                        break
                    start = m.start()

            state = dfa_start
            last_accept_end: int | None = None
            consumed_any = False
            curr = start

            for literal, target_state, lit_len in literal_prefixes:
                if text.startswith(literal, curr):
                    curr += lit_len
                    state = target_state
                    consumed_any = True
                    if accept_flags[state]:
                        last_accept_end = curr
                    break

            while curr < n:
                if self_loop_any_accepts[state]:
                    next_nl = text.find("\n", curr)
                    curr = n if next_nl == -1 else next_nl
                    last_accept_end = curr
                    consumed_any = True
                    break

                char = text[curr]
                tr, any_tr = fast_trans_list[state]
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

                if accept_flags[state]:
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

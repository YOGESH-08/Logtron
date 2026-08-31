"""Hopcroft DFA minimization."""

from __future__ import annotations

from collections import defaultdict

from core.subset import DFA


class HopcroftMinimizer:
    """Minimize a DFA with Hopcroft's partition-refinement algorithm."""

    def __init__(self, dfa: DFA):
        self.dfa = dfa

    def minimize(self) -> DFA:
        if self.dfa.start is None:
            raise ValueError("DFA must have a start state")

        reachable = self._reachable_states()
        accepting = self.dfa.accepts & reachable
        non_accepting = reachable - accepting

        partitions: list[frozenset[int]] = []
        if accepting:
            partitions.append(frozenset(accepting))
        if non_accepting:
            partitions.append(frozenset(non_accepting))

        if not partitions:
            return DFA(alphabet=set(self.dfa.alphabet))

        worklist = partitions.copy()
        predecessors = self._predecessors(reachable)

        while worklist:
            splitter = worklist.pop()

            for symbol in sorted(self.dfa.alphabet):
                affected = self._states_reaching(predecessors, symbol, splitter)
                if not affected:
                    continue

                refined: list[frozenset[int]] = []
                for block in partitions:
                    inside = block & affected
                    outside = block - affected
                    if inside and outside:
                        inside_block = frozenset(inside)
                        outside_block = frozenset(outside)
                        refined.extend([inside_block, outside_block])
                        self._update_worklist(worklist, block, inside_block, outside_block)
                    else:
                        refined.append(block)

                partitions = refined

        ordered_blocks = self._order_blocks(partitions)
        state_to_block = {
            state: block_id
            for block_id, block in enumerate(ordered_blocks)
            for state in block
        }

        minimized = DFA(
            states=set(range(len(ordered_blocks))),
            alphabet=set(self.dfa.alphabet),
            transitions={state: {} for state in range(len(ordered_blocks))},
            start=state_to_block[self.dfa.start],
            accepts={
                block_id
                for block_id, block in enumerate(ordered_blocks)
                if block & self.dfa.accepts
            },
            state_subsets={
                block_id: frozenset(block)
                for block_id, block in enumerate(ordered_blocks)
            },
        )

        for block_id, block in enumerate(ordered_blocks):
            representative = min(block)
            for symbol, target in self.dfa.transitions.get(representative, {}).items():
                if target in state_to_block:
                    minimized.transitions[block_id][symbol] = state_to_block[target]

        return minimized

    def _reachable_states(self) -> set[int]:
        reachable = {self.dfa.start}
        stack = [self.dfa.start]

        while stack:
            state = stack.pop()
            for target in self.dfa.transitions.get(state, {}).values():
                if target not in reachable:
                    reachable.add(target)
                    stack.append(target)

        return reachable

    def _predecessors(self, states: set[int]) -> dict[str, dict[int, set[int]]]:
        predecessors: dict[str, dict[int, set[int]]] = {
            symbol: defaultdict(set)
            for symbol in self.dfa.alphabet
        }

        for source in states:
            for symbol, target in self.dfa.transitions.get(source, {}).items():
                if symbol in self.dfa.alphabet and target in states:
                    predecessors[symbol][target].add(source)

        return predecessors

    def _states_reaching(
        self,
        predecessors: dict[str, dict[int, set[int]]],
        symbol: str,
        splitter: frozenset[int],
    ) -> set[int]:
        affected: set[int] = set()
        for state in splitter:
            affected.update(predecessors[symbol].get(state, set()))
        return affected

    def _update_worklist(
        self,
        worklist: list[frozenset[int]],
        old_block: frozenset[int],
        inside_block: frozenset[int],
        outside_block: frozenset[int],
    ) -> None:
        if old_block in worklist:
            worklist.remove(old_block)
            worklist.append(inside_block)
            worklist.append(outside_block)
            return

        if len(inside_block) <= len(outside_block):
            worklist.append(inside_block)
        else:
            worklist.append(outside_block)

    def _order_blocks(self, partitions: list[frozenset[int]]) -> list[frozenset[int]]:
        start = self.dfa.start
        return sorted(
            partitions,
            key=lambda block: (
                0 if start in block else 1,
                min(block),
            ),
        )


def minimize_dfa(dfa: DFA) -> DFA:
    """Convenience wrapper for HopcroftMinimizer(dfa).minimize()."""
    return HopcroftMinimizer(dfa).minimize()

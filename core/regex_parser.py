"""
Regex Parser & AST Definitions for LogScan DFA.

Provides ASTNode dataclass representing nodes in the regular expression syntax tree
and RegexParser to convert string patterns into AST representation.

Supported AST nodes:
    SYMBOL, ANY, CHAR_CLASS, CONCAT, UNION, STAR, PLUS, OPTIONAL
"""

from dataclasses import dataclass
from typing import Optional, Set, Any, List, Tuple


@dataclass
class ASTNode:
    """
    Abstract Syntax Tree node for regular expressions.
    """
    node_type: str  # SYMBOL, ANY, CHAR_CLASS, CONCAT, UNION, STAR, PLUS, OPTIONAL
    value: Any = None
    left: Optional['ASTNode'] = None
    right: Optional['ASTNode'] = None


class RegexParser:
    """
    Infix Regular Expression Parser using Shunting-Yard algorithm.
    Converts regex pattern string into an ASTNode tree.
    """

    def __init__(self, pattern: str):
        if not pattern:
            raise ValueError("Regex pattern cannot be empty.")
        self.pattern = pattern

    def parse(self) -> ASTNode:
        """
        Parses regex pattern into an ASTNode tree.
        """
        tokens = self._tokenize(self.pattern)
        explicit_tokens = self._insert_explicit_concat(tokens)
        postfix = self._shunting_yard(explicit_tokens)
        return self._build_ast(postfix)

    def _tokenize(self, pattern: str) -> List[Tuple[str, Any]]:
        tokens = []
        i = 0
        n = len(pattern)
        while i < n:
            char = pattern[i]
            if char == '\\':
                if i + 1 < n:
                    tokens.append(('SYMBOL', pattern[i + 1]))
                    i += 2
                else:
                    tokens.append(('SYMBOL', '\\'))
                    i += 1
            elif char == '[':
                j = i + 1
                char_set: Set[str] = set()
                while j < n and pattern[j] != ']':
                    if j + 2 < n and pattern[j + 1] == '-':
                        start_c, end_c = ord(pattern[j]), ord(pattern[j + 2])
                        for c in range(start_c, end_c + 1):
                            char_set.add(chr(c))
                        j += 3
                    else:
                        char_set.add(pattern[j])
                        j += 1
                tokens.append(('CHAR_CLASS', char_set))
                i = j + 1 if j < n else n
            elif char == '.':
                tokens.append(('ANY', '.'))
                i += 1
            elif char in '|*+?()':
                tokens.append(('OPERATOR', char))
                i += 1
            else:
                tokens.append(('SYMBOL', char))
                i += 1
        return tokens

    def _insert_explicit_concat(self, tokens: List[Tuple[str, Any]]) -> List[Tuple[str, Any]]:
        output = []
        for i in range(len(tokens)):
            tok = tokens[i]
            output.append(tok)
            if i + 1 < len(tokens):
                next_tok = tokens[i + 1]
                t1, v1 = tok
                t2, v2 = next_tok

                is_left_term = (t1 in ('SYMBOL', 'ANY', 'CHAR_CLASS') or v1 in ('*', '+', '?', ')'))
                is_right_term = (t2 in ('SYMBOL', 'ANY', 'CHAR_CLASS') or v2 == '(')

                if is_left_term and is_right_term:
                    output.append(('OPERATOR', '.'))
        return output

    def _shunting_yard(self, tokens: List[Tuple[str, Any]]) -> List[Tuple[str, Any]]:
        output = []
        stack: List[Tuple[str, Any]] = []
        precedence = {'*': 3, '+': 3, '?': 3, '.': 2, '|': 1}

        for tok_type, val in tokens:
            if tok_type in ('SYMBOL', 'ANY', 'CHAR_CLASS'):
                output.append((tok_type, val))
            elif val == '(':
                stack.append((tok_type, val))
            elif val == ')':
                while stack and stack[-1][1] != '(':
                    output.append(stack.pop())
                if stack and stack[-1][1] == '(':
                    stack.pop()
            else:
                while stack and stack[-1][1] != '(' and precedence.get(stack[-1][1], 0) >= precedence.get(val, 0):
                    output.append(stack.pop())
                stack.append((tok_type, val))

        while stack:
            output.append(stack.pop())
        return output

    def _build_ast(self, postfix: List[Tuple[str, Any]]) -> ASTNode:
        stack: List[ASTNode] = []
        for tok_type, val in postfix:
            if tok_type == 'SYMBOL':
                stack.append(ASTNode(node_type='SYMBOL', value=val))
            elif tok_type == 'ANY':
                stack.append(ASTNode(node_type='ANY', value='.'))
            elif tok_type == 'CHAR_CLASS':
                stack.append(ASTNode(node_type='CHAR_CLASS', value=val))
            elif val == '*':
                child = stack.pop()
                stack.append(ASTNode(node_type='STAR', left=child))
            elif val == '+':
                child = stack.pop()
                stack.append(ASTNode(node_type='PLUS', left=child))
            elif val == '?':
                child = stack.pop()
                stack.append(ASTNode(node_type='OPTIONAL', left=child))
            elif val == '.':
                right = stack.pop()
                left = stack.pop()
                stack.append(ASTNode(node_type='CONCAT', left=left, right=right))
            elif val == '|':
                right = stack.pop()
                left = stack.pop()
                stack.append(ASTNode(node_type='UNION', left=left, right=right))

        if len(stack) != 1:
            raise ValueError(f"Invalid regex expression: stack size is {len(stack)}")
        return stack[0]

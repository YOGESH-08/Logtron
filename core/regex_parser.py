"""Regular expression parser for the LogScan DFA pipeline.

The parser supports the regular-language subset used by this project: union,
concatenation, postfix repetition, grouping, wildcard, escapes, and character
classes. It returns ASTNode objects consumed by Thompson construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_letters, digits, whitespace
from typing import Any


class RegexSyntaxError(ValueError):
    """Raised when a pattern cannot be parsed as a supported regex."""


@dataclass
class ASTNode:
    node_type: str
    value: Any = None
    left: "ASTNode | None" = None
    right: "ASTNode | None" = None


@dataclass(frozen=True)
class Token:
    kind: str
    value: Any = None

    @property
    def token_type(self) -> str:
        """Compatibility alias used by the original script-style tests."""
        return self.kind


class RegexParser:
    """Parse supported regex syntax into an abstract syntax tree."""

    CONCAT = "CONCAT"
    UNION = "UNION"
    POSTFIX = {"STAR", "PLUS", "OPTIONAL"}
    OPERANDS = {"SYMBOL", "ANY", "CHAR_CLASS"}
    PRECEDENCE = {
        UNION: 1,
        CONCAT: 2,
    }

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.tokens: list[Token] = []
        self.postfix: list[Token] = []

    def parse(self) -> ASTNode:
        self.tokens = self.tokenize()
        tokens = self.insert_concatenation(self.tokens)
        self.postfix = self.to_postfix(tokens)
        return self.build_ast(self.postfix)

    def tokenize(self) -> list[Token]:
        if self.pattern == "":
            raise RegexSyntaxError("empty regular expressions are not supported")

        tokens: list[Token] = []
        i = 0
        while i < len(self.pattern):
            char = self.pattern[i]

            if char == "\\":
                token, i = self._read_escape_token(i + 1)
                tokens.append(token)
                continue

            if char == "[":
                token, i = self._read_character_class(i + 1)
                tokens.append(token)
                continue

            if char == "(":
                tokens.append(Token("LPAREN"))
            elif char == ")":
                tokens.append(Token("RPAREN"))
            elif char == "|":
                tokens.append(Token(self.UNION))
            elif char == "*":
                tokens.append(Token("STAR"))
            elif char == "+":
                tokens.append(Token("PLUS"))
            elif char == "?":
                tokens.append(Token("OPTIONAL"))
            elif char == ".":
                tokens.append(Token("ANY"))
            else:
                tokens.append(Token("SYMBOL", char))
            i += 1

        return tokens

    def insert_concatenation(self, tokens: list[Token]) -> list[Token]:
        if not tokens:
            raise RegexSyntaxError("empty regular expressions are not supported")

        result: list[Token] = []
        previous: Token | None = None

        for token in tokens:
            if previous is not None and self._can_end_atom(previous) and self._can_start_atom(token):
                result.append(Token(self.CONCAT))
            result.append(token)
            previous = token

        return result

    def to_postfix(self, tokens: list[Token]) -> list[Token]:
        output: list[Token] = []
        operators: list[Token] = []

        for token in tokens:
            if token.kind in self.OPERANDS:
                output.append(token)
            elif token.kind in self.POSTFIX:
                output.append(token)
            elif token.kind in {self.CONCAT, self.UNION}:
                while (
                    operators
                    and operators[-1].kind != "LPAREN"
                    and self.PRECEDENCE[operators[-1].kind] >= self.PRECEDENCE[token.kind]
                ):
                    output.append(operators.pop())
                operators.append(token)
            elif token.kind == "LPAREN":
                operators.append(token)
            elif token.kind == "RPAREN":
                while operators and operators[-1].kind != "LPAREN":
                    output.append(operators.pop())
                if not operators:
                    raise RegexSyntaxError("unmatched closing parenthesis")
                operators.pop()
            else:
                raise RegexSyntaxError(f"unknown token {token.kind!r}")

        while operators:
            operator = operators.pop()
            if operator.kind == "LPAREN":
                raise RegexSyntaxError("unmatched opening parenthesis")
            output.append(operator)

        return output

    def build_ast(self, postfix: list[Token]) -> ASTNode:
        stack: list[ASTNode] = []

        for token in postfix:
            if token.kind == "SYMBOL":
                stack.append(ASTNode("SYMBOL", token.value))
            elif token.kind == "ANY":
                stack.append(ASTNode("ANY"))
            elif token.kind == "CHAR_CLASS":
                stack.append(ASTNode("CHAR_CLASS", set(token.value)))
            elif token.kind in self.POSTFIX:
                if not stack:
                    raise RegexSyntaxError(f"operator {self._operator_text(token.kind)!r} has no operand")
                stack.append(ASTNode(token.kind, left=stack.pop()))
            elif token.kind in {self.CONCAT, self.UNION}:
                if len(stack) < 2:
                    raise RegexSyntaxError(f"operator {self._operator_text(token.kind)!r} has too few operands")
                right = stack.pop()
                left = stack.pop()
                stack.append(ASTNode(token.kind, left=left, right=right))
            else:
                raise RegexSyntaxError(f"unknown postfix token {token.kind!r}")

        if len(stack) != 1:
            raise RegexSyntaxError("invalid regular expression")
        return stack[0]

    def _read_escape_token(self, index: int) -> tuple[Token, int]:
        if index >= len(self.pattern):
            raise RegexSyntaxError("dangling escape at end of pattern")

        escaped = self.pattern[index]
        if escaped == "d":
            return Token("CHAR_CLASS", frozenset(digits)), index + 1
        if escaped == "w":
            return Token("CHAR_CLASS", frozenset(ascii_letters + digits + "_")), index + 1
        if escaped == "s":
            return Token("CHAR_CLASS", frozenset(" \t\r\n\f\v")), index + 1
        if escaped == "n":
            return Token("SYMBOL", "\n"), index + 1
        if escaped == "r":
            return Token("SYMBOL", "\r"), index + 1
        if escaped == "t":
            return Token("SYMBOL", "\t"), index + 1

        return Token("SYMBOL", escaped), index + 1

    def _read_character_class(self, index: int) -> tuple[Token, int]:
        characters: set[str] = set()

        if index >= len(self.pattern):
            raise RegexSyntaxError("unterminated character class")

        while index < len(self.pattern):
            if self.pattern[index] == "]":
                if not characters:
                    raise RegexSyntaxError("empty character classes are not supported")
                return Token("CHAR_CLASS", frozenset(characters)), index + 1

            start_chars, index = self._read_class_item(index)
            if (
                index < len(self.pattern)
                and self.pattern[index] == "-"
                and index + 1 < len(self.pattern)
                and self.pattern[index + 1] != "]"
            ):
                if len(start_chars) != 1:
                    raise RegexSyntaxError("character class ranges need single-character bounds")
                end_chars, index = self._read_class_item(index + 1)
                if len(end_chars) != 1:
                    raise RegexSyntaxError("character class ranges need single-character bounds")

                start = next(iter(start_chars))
                end = next(iter(end_chars))
                if ord(start) > ord(end):
                    raise RegexSyntaxError(f"invalid character range {start}-{end}")
                characters.update(chr(code) for code in range(ord(start), ord(end) + 1))
            else:
                characters.update(start_chars)

        raise RegexSyntaxError("unterminated character class")

    def _read_class_item(self, index: int) -> tuple[set[str], int]:
        char = self.pattern[index]
        if char == "\\":
            if index + 1 >= len(self.pattern):
                raise RegexSyntaxError("dangling escape in character class")
            escaped = self.pattern[index + 1]
            if escaped == "d":
                return set(digits), index + 2
            if escaped == "w":
                return set(ascii_letters + digits + "_"), index + 2
            if escaped == "s":
                return set(whitespace), index + 2
            if escaped == "n":
                return {"\n"}, index + 2
            if escaped == "r":
                return {"\r"}, index + 2
            if escaped == "t":
                return {"\t"}, index + 2
            return {escaped}, index + 2

        return {char}, index + 1

    def _can_end_atom(self, token: Token) -> bool:
        return token.kind in self.OPERANDS or token.kind == "RPAREN" or token.kind in self.POSTFIX

    def _can_start_atom(self, token: Token) -> bool:
        return token.kind in self.OPERANDS or token.kind == "LPAREN"

    def _operator_text(self, kind: str) -> str:
        return {
            self.CONCAT: "concatenation",
            self.UNION: "|",
            "STAR": "*",
            "PLUS": "+",
            "OPTIONAL": "?",
        }.get(kind, kind)


def parse_regex(pattern: str) -> ASTNode:
    return RegexParser(pattern).parse()


def ast_to_string(node: ASTNode | None, indent: int = 0) -> str:
    """Return a readable multiline representation of an AST."""
    if node is None:
        return " " * indent + "None"

    label = node.node_type
    if node.value is not None:
        label += f"({node.value!r})"

    lines = [" " * indent + label]
    if node.left is not None:
        lines.append(ast_to_string(node.left, indent + 2))
    if node.right is not None:
        lines.append(ast_to_string(node.right, indent + 2))
    return "\n".join(lines)

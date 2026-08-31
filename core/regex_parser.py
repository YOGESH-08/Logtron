"""
Regex Parser for LogScan DFA

Supported syntax:
    |       Union
    *       Kleene star
    +       One or more
    ?       Zero or one
    .       Any character
    (...)   Grouping
    [...]   Character class
    [a-z]   Character range
    \\      Escape character

The parser converts a regex into an AST.

Example:

    ab|c*

becomes approximately:

            UNION
           /     \
        CONCAT    STAR
        /   \      |
       a     b     c
"""

# ============================================================
# IMPORTS
# ============================================================

from dataclasses import dataclass
from typing import List, Optional


# ============================================================
# MODULE 1: AST NODE
# ============================================================

@dataclass
class ASTNode:
    """
    Represents one node in the regular-expression AST.

    node_type:
        SYMBOL
        ANY
        CONCAT
        UNION
        STAR
        PLUS
        OPTIONAL
        CHAR_CLASS

    value:
        Used by SYMBOL and CHAR_CLASS.
    """

    node_type: str
    value: Optional[object] = None
    left: Optional["ASTNode"] = None
    right: Optional["ASTNode"] = None


# ============================================================
# MODULE 2: TOKEN
# ============================================================

@dataclass
class Token:
    """
    Internal token used by the parser.
    """

    token_type: str
    value: Optional[object] = None


# ============================================================
# MODULE 3: REGEX PARSER SETUP
# ============================================================

class RegexParser:
    """
    Converts a regular expression into an AST.

    Parsing strategy:

        1. Tokenize the regex
        2. Insert explicit concatenation operators
        3. Convert infix expression to postfix
        4. Build AST from postfix
    """

    # Operators supported by the parser
    OPERATORS = {
        "|",
        "*",
        "+",
        "?",
        ".",
        "(",
        ")",
        "CONCAT",
    }

    # Operator precedence
    PRECEDENCE = {
        "|": 1,
        "CONCAT": 2,
        "*": 3,
        "+": 3,
        "?": 3,
    }

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.tokens: List[Token] = []
        self.postfix: List[Token] = []


    # ========================================================
    # MODULE 16: PUBLIC PARSE API
    # ========================================================

    def parse(self) -> ASTNode:
        """
        Parse the regex and return the AST.
        """

        if not self.pattern:
            raise ValueError(
                "Regular expression cannot be empty."
            )

        self.tokens = self._tokenize(self.pattern)

        self.tokens = self._insert_concatenation(
            self.tokens
        )

        self.postfix = self._to_postfix(
            self.tokens
        )

        return self._postfix_to_ast(
            self.postfix
        )


    # ========================================================
    # MODULES 4, 5, 6: TOKENIZATION
    # Basic symbols, operators, and escape sequences
    # ========================================================

    def _tokenize(
        self,
        pattern: str
    ) -> List[Token]:
        """
        Convert raw regex string into tokens.

        Examples:

            abc
            -> a, b, c

            a|b
            -> a, |, b

            \\*
            -> SYMBOL(*)
        """

        tokens = []
        i = 0

        while i < len(pattern):

            character = pattern[i]

            # ------------------------------------------------
            # MODULE 6: Escape Sequence
            # ------------------------------------------------

            if character == "\\":

                if i + 1 >= len(pattern):
                    raise ValueError(
                        "Dangling escape character at end of regex."
                    )

                i += 1

                escaped_char = pattern[i]

                tokens.append(
                    Token(
                        "SYMBOL",
                        escaped_char
                    )
                )

            # ------------------------------------------------
            # MODULES 7, 8: Character Class and Range
            # ------------------------------------------------

            elif character == "[":

                char_class, new_index = (
                    self._parse_character_class(
                        pattern,
                        i
                    )
                )

                tokens.append(
                    Token(
                        "CHAR_CLASS",
                        char_class
                    )
                )

                i = new_index

            # ------------------------------------------------
            # MODULE 5: Operators
            # ------------------------------------------------

            elif character in {
                "|",
                "*",
                "+",
                "?",
                "(",
                ")",
                ".",
            }:

                # Dot means ANY character
                if character == ".":

                    tokens.append(
                        Token("ANY")
                    )

                else:

                    tokens.append(
                        Token(character)
                    )

            # ------------------------------------------------
            # MODULE 4: Normal Character
            # ------------------------------------------------

            else:

                tokens.append(
                    Token(
                        "SYMBOL",
                        character
                    )
                )

            i += 1

        return tokens


    # ========================================================
    # MODULES 7, 8: CHARACTER CLASS AND CHARACTER RANGE
    # ========================================================

    def _parse_character_class(
        self,
        pattern: str,
        start: int
    ):
        """
        Parse:

            [abc]
            [a-z]
            [a-zA-Z0-9]

        Returns:

            (set_of_characters, closing_bracket_index)
        """

        characters = set()

        i = start + 1

        if i >= len(pattern):

            raise ValueError(
                "Unclosed character class."
            )

        while (
            i < len(pattern)
            and pattern[i] != "]"
        ):

            # ------------------------------------------------
            # Escape inside character class
            # ------------------------------------------------

            if pattern[i] == "\\":

                if i + 1 >= len(pattern):

                    raise ValueError(
                        "Dangling escape inside character class."
                    )

                characters.add(
                    pattern[i + 1]
                )

                i += 2
                continue

            # ------------------------------------------------
            # MODULE 8: Character Range
            # ------------------------------------------------

            if (
                i + 2 < len(pattern)
                and pattern[i + 1] == "-"
                and pattern[i + 2] != "]"
            ):

                start_char = pattern[i]
                end_char = pattern[i + 2]

                if ord(start_char) > ord(end_char):

                    raise ValueError(
                        f"Invalid character range: "
                        f"{start_char}-{end_char}"
                    )

                for code in range(
                    ord(start_char),
                    ord(end_char) + 1
                ):

                    characters.add(
                        chr(code)
                    )

                i += 3
                continue

            # ------------------------------------------------
            # Normal character
            # ------------------------------------------------

            characters.add(
                pattern[i]
            )

            i += 1

        if i >= len(pattern):

            raise ValueError(
                "Unclosed character class."
            )

        if not characters:

            raise ValueError(
                "Empty character class."
            )

        return characters, i


    # ========================================================
    # MODULE 9: CONCATENATION HELPERS
    # ========================================================

    @staticmethod
    def _can_end_expression(token: Token) -> bool:
        """
        Return True if the token can appear at the end
        of a regular-expression expression.
        """

        return token.token_type in {
            "SYMBOL",
            "ANY",
            "CHAR_CLASS",
            ")",
            "*",
            "+",
            "?",
        }

    @staticmethod
    def _can_start_expression(token: Token) -> bool:
        """
        Return True if the token can appear at the beginning
        of a regular-expression expression.
        """

        return token.token_type in {
            "SYMBOL",
            "ANY",
            "CHAR_CLASS",
            "(",
        }


    # ========================================================
    # MODULE 10: CONCATENATION INSERTION
    # ========================================================

    def _insert_concatenation(
        self,
        tokens: List[Token]
    ) -> List[Token]:
        """
        Insert explicit CONCAT operators.

        Example:

            ab

        becomes:

            a CONCAT b

        Another example:

            a(b|c)

        becomes:

            a CONCAT (b|c)
        """

        result = []

        for i, current in enumerate(tokens):

            result.append(current)

            if i == len(tokens) - 1:
                continue

            next_token = tokens[i + 1]

            if (
                self._can_end_expression(current)
                and self._can_start_expression(next_token)
            ):

                result.append(
                    Token("CONCAT")
                )

        return result


    # ========================================================
    # MODULES 11, 12: INFIX TO POSTFIX
    # Shunting-Yard Algorithm + Precedence + Parentheses
    # ========================================================

    def _to_postfix(
        self,
        tokens: List[Token]
    ) -> List[Token]:
        """
        Convert infix regex expression to postfix notation.

        Example:

            a|bc

        becomes:

            a b c CONCAT |
        """

        output = []
        stack = []

        for token in tokens:

            token_type = token.token_type

            # ------------------------------------------------
            # Operands
            # ------------------------------------------------

            if token_type in {
                "SYMBOL",
                "ANY",
                "CHAR_CLASS",
            }:

                output.append(token)

            # ------------------------------------------------
            # Left Parenthesis
            # ------------------------------------------------

            elif token_type == "(":

                stack.append(token_type)

            # ------------------------------------------------
            # Right Parenthesis
            # ------------------------------------------------

            elif token_type == ")":

                found_left = False

                while stack:

                    top = stack.pop()

                    if top == "(":
                        found_left = True
                        break

                    output.append(
                        Token(top)
                    )

                if not found_left:

                    raise ValueError(
                        "Mismatched closing parenthesis."
                    )

            # ------------------------------------------------
            # Unary Operators
            # ------------------------------------------------

            elif token_type in {
                "*",
                "+",
                "?",
            }:

                output.append(token)

            # ------------------------------------------------
            # Binary Operators
            # ------------------------------------------------

            elif token_type in {
                "|",
                "CONCAT",
            }:

                while (
                    stack
                    and stack[-1] != "("
                    and self.PRECEDENCE[stack[-1]]
                    >= self.PRECEDENCE[token_type]
                ):

                    output.append(
                        Token(
                            stack.pop()
                        )
                    )

                stack.append(token_type)

            else:

                raise ValueError(
                    f"Unknown token: {token_type}"
                )

        # ----------------------------------------------------
        # Empty remaining operators
        # ----------------------------------------------------

        while stack:

            top = stack.pop()

            if top == "(":

                raise ValueError(
                    "Mismatched opening parenthesis."
                )

            output.append(
                Token(top)
            )

        return output


    # ========================================================
    # MODULES 13, 14, 15: POSTFIX TO AST
    # Operands + Unary Operators + Binary Operators
    # ========================================================

    def _postfix_to_ast(
        self,
        postfix: List[Token]
    ) -> ASTNode:
        """
        Build AST from postfix expression.
        """

        stack: List[ASTNode] = []

        for token in postfix:

            token_type = token.token_type

            # ------------------------------------------------
            # MODULE 13: Operands
            # ------------------------------------------------

            if token_type == "SYMBOL":

                stack.append(
                    ASTNode(
                        node_type="SYMBOL",
                        value=token.value
                    )
                )

            elif token_type == "ANY":

                stack.append(
                    ASTNode(
                        node_type="ANY"
                    )
                )

            elif token_type == "CHAR_CLASS":

                stack.append(
                    ASTNode(
                        node_type="CHAR_CLASS",
                        value=token.value
                    )
                )

            # ------------------------------------------------
            # MODULE 14: Unary Operators
            # ------------------------------------------------

            elif token_type in {
                "*",
                "+",
                "?",
            }:

                if not stack:

                    raise ValueError(
                        f"Missing operand for "
                        f"'{token_type}'."
                    )

                operand = stack.pop()

                node_type = {
                    "*": "STAR",
                    "+": "PLUS",
                    "?": "OPTIONAL",
                }[token_type]

                stack.append(
                    ASTNode(
                        node_type=node_type,
                        left=operand
                    )
                )

            # ------------------------------------------------
            # MODULE 15: Binary Operators
            # ------------------------------------------------

            elif token_type in {
                "CONCAT",
                "|",
            }:

                if len(stack) < 2:

                    raise ValueError(
                        f"Missing operands for "
                        f"'{token_type}'."
                    )

                right = stack.pop()
                left = stack.pop()

                node_type = (
                    "CONCAT"
                    if token_type == "CONCAT"
                    else "UNION"
                )

                stack.append(
                    ASTNode(
                        node_type=node_type,
                        left=left,
                        right=right
                    )
                )

            else:

                raise ValueError(
                    f"Unknown postfix token: "
                    f"{token_type}"
                )

        # ----------------------------------------------------
        # Exactly one AST must remain
        # ----------------------------------------------------

        if len(stack) != 1:

            raise ValueError(
                "Invalid regular expression."
            )

        return stack[0]


# ============================================================
# MODULE 17: AST DEBUGGING / DISPLAY
# ============================================================

def ast_to_string(
    node: ASTNode,
    depth: int = 0
) -> str:
    """
    Convert AST into a readable tree representation.

    Useful while debugging the parser.
    """

    indent = "  " * depth

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    if node.node_type == "SYMBOL":

        return (
            f"{indent}SYMBOL({node.value})"
        )

    # --------------------------------------------------------
    # ANY
    # --------------------------------------------------------

    if node.node_type == "ANY":

        return (
            f"{indent}ANY(.)"
        )

    # --------------------------------------------------------
    # CHARACTER CLASS
    # --------------------------------------------------------

    if node.node_type == "CHAR_CLASS":

        chars = "".join(
            sorted(node.value)
        )

        return (
            f"{indent}CHAR_CLASS([{chars}])"
        )

    # --------------------------------------------------------
    # Unary Nodes
    # --------------------------------------------------------

    if node.node_type in {
        "STAR",
        "PLUS",
        "OPTIONAL",
    }:

        return (
            f"{indent}{node.node_type}\n"
            f"{ast_to_string(node.left, depth + 1)}"
        )

    # --------------------------------------------------------
    # Binary Nodes
    # --------------------------------------------------------

    if node.node_type in {
        "CONCAT",
        "UNION",
    }:

        return (
            f"{indent}{node.node_type}\n"
            f"{ast_to_string(node.left, depth + 1)}\n"
            f"{ast_to_string(node.right, depth + 1)}"
        )

    return f"{indent}{node.node_type}""""
Regex Parser for LogScan DFA

Supported syntax:
    |       Union
    *       Kleene star
    +       One or more
    ?       Zero or one
    .       Any character
    (...)   Grouping
    [...]   Character class
    [a-z]   Character range
    \\      Escape character

The parser converts a regex into an AST.

Example:

    ab|c*

becomes approximately:

            UNION
           /     \
        CONCAT    STAR
        /   \      |
       a     b     c
"""

# ============================================================
# IMPORTS
# ============================================================

from dataclasses import dataclass
from typing import List, Optional


# ============================================================
# MODULE 1: AST NODE
# ============================================================

@dataclass
class ASTNode:
    """
    Represents one node in the regular-expression AST.

    node_type:
        SYMBOL
        ANY
        CONCAT
        UNION
        STAR
        PLUS
        OPTIONAL
        CHAR_CLASS

    value:
        Used by SYMBOL and CHAR_CLASS.
    """

    node_type: str
    value: Optional[object] = None
    left: Optional["ASTNode"] = None
    right: Optional["ASTNode"] = None


# ============================================================
# MODULE 2: TOKEN
# ============================================================

@dataclass
class Token:
    """
    Internal token used by the parser.
    """

    token_type: str
    value: Optional[object] = None


# ============================================================
# MODULE 3: REGEX PARSER SETUP
# ============================================================

class RegexParser:
    """
    Converts a regular expression into an AST.

    Parsing strategy:

        1. Tokenize the regex
        2. Insert explicit concatenation operators
        3. Convert infix expression to postfix
        4. Build AST from postfix
    """

    # Operators supported by the parser
    OPERATORS = {
        "|",
        "*",
        "+",
        "?",
        ".",
        "(",
        ")",
        "CONCAT",
    }

    # Operator precedence
    PRECEDENCE = {
        "|": 1,
        "CONCAT": 2,
        "*": 3,
        "+": 3,
        "?": 3,
    }

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.tokens: List[Token] = []
        self.postfix: List[Token] = []


    # ========================================================
    # MODULE 16: PUBLIC PARSE API
    # ========================================================

    def parse(self) -> ASTNode:
        """
        Parse the regex and return the AST.
        """

        if not self.pattern:
            raise ValueError(
                "Regular expression cannot be empty."
            )

        self.tokens = self._tokenize(self.pattern)

        self.tokens = self._insert_concatenation(
            self.tokens
        )

        self.postfix = self._to_postfix(
            self.tokens
        )

        return self._postfix_to_ast(
            self.postfix
        )


    # ========================================================
    # MODULES 4, 5, 6: TOKENIZATION
    # Basic symbols, operators, and escape sequences
    # ========================================================

    def _tokenize(
        self,
        pattern: str
    ) -> List[Token]:
        """
        Convert raw regex string into tokens.

        Examples:

            abc
            -> a, b, c

            a|b
            -> a, |, b

            \\*
            -> SYMBOL(*)
        """

        tokens = []
        i = 0

        while i < len(pattern):

            character = pattern[i]

            # ------------------------------------------------
            # MODULE 6: Escape Sequence
            # ------------------------------------------------

            if character == "\\":

                if i + 1 >= len(pattern):
                    raise ValueError(
                        "Dangling escape character at end of regex."
                    )

                i += 1

                escaped_char = pattern[i]

                tokens.append(
                    Token(
                        "SYMBOL",
                        escaped_char
                    )
                )

            # ------------------------------------------------
            # MODULES 7, 8: Character Class and Range
            # ------------------------------------------------

            elif character == "[":

                char_class, new_index = (
                    self._parse_character_class(
                        pattern,
                        i
                    )
                )

                tokens.append(
                    Token(
                        "CHAR_CLASS",
                        char_class
                    )
                )

                i = new_index

            # ------------------------------------------------
            # MODULE 5: Operators
            # ------------------------------------------------

            elif character in {
                "|",
                "*",
                "+",
                "?",
                "(",
                ")",
                ".",
            }:

                # Dot means ANY character
                if character == ".":

                    tokens.append(
                        Token("ANY")
                    )

                else:

                    tokens.append(
                        Token(character)
                    )

            # ------------------------------------------------
            # MODULE 4: Normal Character
            # ------------------------------------------------

            else:

                tokens.append(
                    Token(
                        "SYMBOL",
                        character
                    )
                )

            i += 1

        return tokens


    # ========================================================
    # MODULES 7, 8: CHARACTER CLASS AND CHARACTER RANGE
    # ========================================================

    def _parse_character_class(
        self,
        pattern: str,
        start: int
    ):
        """
        Parse:

            [abc]
            [a-z]
            [a-zA-Z0-9]

        Returns:

            (set_of_characters, closing_bracket_index)
        """

        characters = set()

        i = start + 1

        if i >= len(pattern):

            raise ValueError(
                "Unclosed character class."
            )

        while (
            i < len(pattern)
            and pattern[i] != "]"
        ):

            # ------------------------------------------------
            # Escape inside character class
            # ------------------------------------------------

            if pattern[i] == "\\":

                if i + 1 >= len(pattern):

                    raise ValueError(
                        "Dangling escape inside character class."
                    )

                characters.add(
                    pattern[i + 1]
                )

                i += 2
                continue

            # ------------------------------------------------
            # MODULE 8: Character Range
            # ------------------------------------------------

            if (
                i + 2 < len(pattern)
                and pattern[i + 1] == "-"
                and pattern[i + 2] != "]"
            ):

                start_char = pattern[i]
                end_char = pattern[i + 2]

                if ord(start_char) > ord(end_char):

                    raise ValueError(
                        f"Invalid character range: "
                        f"{start_char}-{end_char}"
                    )

                for code in range(
                    ord(start_char),
                    ord(end_char) + 1
                ):

                    characters.add(
                        chr(code)
                    )

                i += 3
                continue

            # ------------------------------------------------
            # Normal character
            # ------------------------------------------------

            characters.add(
                pattern[i]
            )

            i += 1

        if i >= len(pattern):

            raise ValueError(
                "Unclosed character class."
            )

        if not characters:

            raise ValueError(
                "Empty character class."
            )

        return characters, i


    # ========================================================
    # MODULE 9: CONCATENATION HELPERS
    # ========================================================

    @staticmethod
    def _can_end_expression(token: Token) -> bool:
        """
        Return True if the token can appear at the end
        of a regular-expression expression.
        """

        return token.token_type in {
            "SYMBOL",
            "ANY",
            "CHAR_CLASS",
            ")",
            "*",
            "+",
            "?",
        }

    @staticmethod
    def _can_start_expression(token: Token) -> bool:
        """
        Return True if the token can appear at the beginning
        of a regular-expression expression.
        """

        return token.token_type in {
            "SYMBOL",
            "ANY",
            "CHAR_CLASS",
            "(",
        }


    # ========================================================
    # MODULE 10: CONCATENATION INSERTION
    # ========================================================

    def _insert_concatenation(
        self,
        tokens: List[Token]
    ) -> List[Token]:
        """
        Insert explicit CONCAT operators.

        Example:

            ab

        becomes:

            a CONCAT b

        Another example:

            a(b|c)

        becomes:

            a CONCAT (b|c)
        """

        result = []

        for i, current in enumerate(tokens):

            result.append(current)

            if i == len(tokens) - 1:
                continue

            next_token = tokens[i + 1]

            if (
                self._can_end_expression(current)
                and self._can_start_expression(next_token)
            ):

                result.append(
                    Token("CONCAT")
                )

        return result


    # ========================================================
    # MODULES 11, 12: INFIX TO POSTFIX
    # Shunting-Yard Algorithm + Precedence + Parentheses
    # ========================================================

    def _to_postfix(
        self,
        tokens: List[Token]
    ) -> List[Token]:
        """
        Convert infix regex expression to postfix notation.

        Example:

            a|bc

        becomes:

            a b c CONCAT |
        """

        output = []
        stack = []

        for token in tokens:

            token_type = token.token_type

            # ------------------------------------------------
            # Operands
            # ------------------------------------------------

            if token_type in {
                "SYMBOL",
                "ANY",
                "CHAR_CLASS",
            }:

                output.append(token)

            # ------------------------------------------------
            # Left Parenthesis
            # ------------------------------------------------

            elif token_type == "(":

                stack.append(token_type)

            # ------------------------------------------------
            # Right Parenthesis
            # ------------------------------------------------

            elif token_type == ")":

                found_left = False

                while stack:

                    top = stack.pop()

                    if top == "(":
                        found_left = True
                        break

                    output.append(
                        Token(top)
                    )

                if not found_left:

                    raise ValueError(
                        "Mismatched closing parenthesis."
                    )

            # ------------------------------------------------
            # Unary Operators
            # ------------------------------------------------

            elif token_type in {
                "*",
                "+",
                "?",
            }:

                output.append(token)

            # ------------------------------------------------
            # Binary Operators
            # ------------------------------------------------

            elif token_type in {
                "|",
                "CONCAT",
            }:

                while (
                    stack
                    and stack[-1] != "("
                    and self.PRECEDENCE[stack[-1]]
                    >= self.PRECEDENCE[token_type]
                ):

                    output.append(
                        Token(
                            stack.pop()
                        )
                    )

                stack.append(token_type)

            else:

                raise ValueError(
                    f"Unknown token: {token_type}"
                )

        # ----------------------------------------------------
        # Empty remaining operators
        # ----------------------------------------------------

        while stack:

            top = stack.pop()

            if top == "(":

                raise ValueError(
                    "Mismatched opening parenthesis."
                )

            output.append(
                Token(top)
            )

        return output


    # ========================================================
    # MODULES 13, 14, 15: POSTFIX TO AST
    # Operands + Unary Operators + Binary Operators
    # ========================================================

    def _postfix_to_ast(
        self,
        postfix: List[Token]
    ) -> ASTNode:
        """
        Build AST from postfix expression.
        """

        stack: List[ASTNode] = []

        for token in postfix:

            token_type = token.token_type

            # ------------------------------------------------
            # MODULE 13: Operands
            # ------------------------------------------------

            if token_type == "SYMBOL":

                stack.append(
                    ASTNode(
                        node_type="SYMBOL",
                        value=token.value
                    )
                )

            elif token_type == "ANY":

                stack.append(
                    ASTNode(
                        node_type="ANY"
                    )
                )

            elif token_type == "CHAR_CLASS":

                stack.append(
                    ASTNode(
                        node_type="CHAR_CLASS",
                        value=token.value
                    )
                )

            # ------------------------------------------------
            # MODULE 14: Unary Operators
            # ------------------------------------------------

            elif token_type in {
                "*",
                "+",
                "?",
            }:

                if not stack:

                    raise ValueError(
                        f"Missing operand for "
                        f"'{token_type}'."
                    )

                operand = stack.pop()

                node_type = {
                    "*": "STAR",
                    "+": "PLUS",
                    "?": "OPTIONAL",
                }[token_type]

                stack.append(
                    ASTNode(
                        node_type=node_type,
                        left=operand
                    )
                )

            # ------------------------------------------------
            # MODULE 15: Binary Operators
            # ------------------------------------------------

            elif token_type in {
                "CONCAT",
                "|",
            }:

                if len(stack) < 2:

                    raise ValueError(
                        f"Missing operands for "
                        f"'{token_type}'."
                    )

                right = stack.pop()
                left = stack.pop()

                node_type = (
                    "CONCAT"
                    if token_type == "CONCAT"
                    else "UNION"
                )

                stack.append(
                    ASTNode(
                        node_type=node_type,
                        left=left,
                        right=right
                    )
                )

            else:

                raise ValueError(
                    f"Unknown postfix token: "
                    f"{token_type}"
                )

        # ----------------------------------------------------
        # Exactly one AST must remain
        # ----------------------------------------------------

        if len(stack) != 1:

            raise ValueError(
                "Invalid regular expression."
            )

        return stack[0]


# ============================================================
# MODULE 17: AST DEBUGGING / DISPLAY
# ============================================================

def ast_to_string(
    node: ASTNode,
    depth: int = 0
) -> str:
    """
    Convert AST into a readable tree representation.

    Useful while debugging the parser.
    """

    indent = "  " * depth

    # --------------------------------------------------------
    # SYMBOL
    # --------------------------------------------------------

    if node.node_type == "SYMBOL":

        return (
            f"{indent}SYMBOL({node.value})"
        )

    # --------------------------------------------------------
    # ANY
    # --------------------------------------------------------

    if node.node_type == "ANY":

        return (
            f"{indent}ANY(.)"
        )

    # --------------------------------------------------------
    # CHARACTER CLASS
    # --------------------------------------------------------

    if node.node_type == "CHAR_CLASS":

        chars = "".join(
            sorted(node.value)
        )

        return (
            f"{indent}CHAR_CLASS([{chars}])"
        )

    # --------------------------------------------------------
    # Unary Nodes
    # --------------------------------------------------------

    if node.node_type in {
        "STAR",
        "PLUS",
        "OPTIONAL",
    }:

        return (
            f"{indent}{node.node_type}\n"
            f"{ast_to_string(node.left, depth + 1)}"
        )

    # --------------------------------------------------------
    # Binary Nodes
    # --------------------------------------------------------

    if node.node_type in {
        "CONCAT",
        "UNION",
    }:

        return (
            f"{indent}{node.node_type}\n"
            f"{ast_to_string(node.left, depth + 1)}\n"
            f"{ast_to_string(node.right, depth + 1)}"
        )

    return f"{indent}{node.node_type}"
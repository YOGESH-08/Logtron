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

#Imports

from dataclasses import dataclass
from typing import List, Optional


#AST Node

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

    node_type : str
    value : Optional[object] = None
    left : Optional["ASTNode"] = None
    right : Optional["ASTNode"] = None



#Token

@dataclass
class Token:
    """
    Internal Token used by the parser
    """

    token_type : str
    value : Optional[object] = None



#Regex Parser

class RegexParser:
    """
    Converts a regular expression into an AST.

    Parsing strategy:
        1. Tokenize the regex
        2. Insert explicit concatenation operators
        3. Convert infix expression to postfix
        4. Build AST from postfix
    """

    #Operators supported by the parser
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

    #Operator Precedence
    PRECEDENCE = {
        "|" : 1,
        "CONCAT" : 2,
        "*" : 3,
        "+" : 3,
        "?" : 3,
    }

    def __init__(self, pattern : str):
        self.pattern = pattern
        self.tokens : List[Token] = []
        self.postfix : List[Token] = []



#Tokenization

def _tokenize(self, pattern : str) -> List[Token]:
    """
    Convert raw regex string into tokens.

    Examples:

        abc
        -> a, b, c

        a|b
        -> a, |, b
    """

    tokens = []
    i = 0

    while i < len(pattern):
        character = pattern[i]

        #Operators
        if character in {"|", "*", "+", "?", ".", "(", ")"}:

            #Dot represents ANY Character
            if character == ".":
                tokens.append(
                    Token("ANY")
                )
            else:
                tokens.append(
                    Token(character)
                )

        #Normal Character
        else:
            tokens.append(
                Token("SYMBOL", character)
            )

        i += 1

    return tokens
"""
Tests for the LogScan DFA Regex Parser.
"""

from core.regex_parser import RegexParser, ast_to_string


# ============================================================
# TEST HELPER
# ============================================================

def run_test(name, pattern):
    """
    Parse a regex and display the generated AST.
    """

    print("\n" + "=" * 60)
    print(f"TEST: {name}")
    print(f"REGEX: {pattern}")
    print("=" * 60)

    try:
        parser = RegexParser(pattern)

        ast = parser.parse()

        print("\nTOKENS:")

        for token in parser.tokens:
            print(
                f"  {token.token_type}: "
                f"{token.value}"
            )

        print("\nPOSTFIX:")

        for token in parser.postfix:
            print(
                f"{token.token_type}",
                end=" "
            )

        print("\n\nAST:")

        print(
            ast_to_string(ast)
        )

        print("\nRESULT: PASSED")

    except ValueError as error:

        print(f"\nRESULT: FAILED")
        print(f"ERROR: {error}")


# ============================================================
# TEST 1: BASIC SYMBOLS
# ============================================================

run_test(
    "Basic Concatenation",
    "abc"
)


# ============================================================
# TEST 2: UNION
# ============================================================

run_test(
    "Union",
    "a|b"
)


# ============================================================
# TEST 3: CONCATENATION AND UNION
# ============================================================

run_test(
    "Concatenation and Union",
    "ab|c"
)


# ============================================================
# TEST 4: KLEENE STAR
# ============================================================

run_test(
    "Kleene Star",
    "a*"
)


# ============================================================
# TEST 5: STAR WITH CONCATENATION
# ============================================================

run_test(
    "Star and Concatenation",
    "a*b"
)


# ============================================================
# TEST 6: PLUS OPERATOR
# ============================================================

run_test(
    "One or More",
    "a+"
)


# ============================================================
# TEST 7: OPTIONAL OPERATOR
# ============================================================

run_test(
    "Optional",
    "a?"
)


# ============================================================
# TEST 8: ANY CHARACTER
# ============================================================

run_test(
    "Any Character",
    "a.b"
)


# ============================================================
# TEST 9: GROUPING
# ============================================================

run_test(
    "Grouping",
    "(a|b)c"
)


# ============================================================
# TEST 10: NESTED GROUPING
# ============================================================

run_test(
    "Nested Grouping",
    "a(b|c)*"
)


# ============================================================
# TEST 11: CHARACTER CLASS
# ============================================================

run_test(
    "Character Class",
    "[abc]"
)


# ============================================================
# TEST 12: CHARACTER RANGE
# ============================================================

run_test(
    "Character Range",
    "[a-z]"
)


# ============================================================
# TEST 13: MULTIPLE RANGES
# ============================================================

run_test(
    "Multiple Character Ranges",
    "[a-zA-Z0-9]"
)


# ============================================================
# TEST 14: ESCAPED OPERATOR
# ============================================================

run_test(
    "Escaped Star",
    r"a\*b"
)


# ============================================================
# TEST 15: COMPLEX EXPRESSION
# ============================================================

run_test(
    "Complex Expression",
    "(ab|c*)d+"
)


# ============================================================
# INVALID REGEX TESTS
# ============================================================

def run_invalid_test(name, pattern):
    """
    Test that an invalid regex raises ValueError.
    """

    print("\n" + "=" * 60)
    print(f"INVALID TEST: {name}")
    print(f"REGEX: {pattern}")
    print("=" * 60)

    try:

        parser = RegexParser(pattern)

        parser.parse()

        print("\nRESULT: FAILED")
        print("Expected an error but parsing succeeded.")

    except ValueError as error:

        print("\nRESULT: PASSED")
        print(f"EXPECTED ERROR: {error}")


# ============================================================
# INVALID TEST 1: EMPTY REGEX
# ============================================================

run_invalid_test(
    "Empty Regex",
    ""
)


# ============================================================
# INVALID TEST 2: DANGLING ESCAPE
# ============================================================

run_invalid_test(
    "Dangling Escape",
    "a\\"
)


# ============================================================
# INVALID TEST 3: UNCLOSED CHARACTER CLASS
# ============================================================

run_invalid_test(
    "Unclosed Character Class",
    "[abc"
)


# ============================================================
# INVALID TEST 4: EMPTY CHARACTER CLASS
# ============================================================

run_invalid_test(
    "Empty Character Class",
    "[]"
)


# ============================================================
# INVALID TEST 5: INVALID RANGE
# ============================================================

run_invalid_test(
    "Invalid Character Range",
    "[z-a]"
)


# ============================================================
# INVALID TEST 6: MISMATCHED OPENING PARENTHESIS
# ============================================================

run_invalid_test(
    "Mismatched Opening Parenthesis",
    "(ab"
)


# ============================================================
# INVALID TEST 7: MISMATCHED CLOSING PARENTHESIS
# ============================================================

run_invalid_test(
    "Mismatched Closing Parenthesis",
    "ab)"
)


# ============================================================
# INVALID TEST 8: MISSING UNION OPERAND
# ============================================================

run_invalid_test(
    "Missing Union Operand",
    "a|"
)


# ============================================================
# TEST COMPLETE
# ============================================================

print("\n" + "=" * 60)
print("ALL REGEX PARSER TESTS COMPLETED")
print("=" * 60)
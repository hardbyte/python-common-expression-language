"""
Pygments lexer for Common Expression Language (CEL).

Provides syntax highlighting for CEL expressions in Textual TextArea widgets.
"""

__all__ = ["CELLexer"]

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)


class CELLexer(RegexLexer):
    """
    Lexer for Common Expression Language (CEL).

    CEL is a non-Turing complete expression language designed for
    safely evaluating expressions in security policies, rules, and more.
    """

    name = "CEL"
    aliases = ["cel"]
    filenames = ["*.cel"]
    mimetypes = ["text/x-cel"]

    tokens = {
        "root": [
            # Keywords - boolean literals
            (words(("true", "false", "null"), suffix=r"\b"), Keyword.Constant),
            # Keywords - operators
            (words(("in", "has"), suffix=r"\b"), Keyword),
            # String literals - double quoted
            (r'"[^"\\]*(?:\\.[^"\\]*)*"', String.Double),
            # String literals - single quoted
            (r"'[^'\\]*(?:\\.[^'\\]*)*'", String.Single),
            # Numbers - integers and floats with optional scientific notation
            (r"\d+\.?\d*([eE][+-]?\d+)?", Number),
            # Comparison operators
            (r"(==|!=|<=|>=|<|>)", Operator),
            # Logical operators
            (r"(&&|\|\||!)", Operator),
            # Arithmetic operators
            (r"[+\-*/%]", Operator),
            # Ternary operator
            (r"(\?|:)", Operator),
            # Brackets and delimiters
            (r"[(){}\[\],.]", Punctuation),
            # Function calls - identifier followed by (
            (
                r"([a-zA-Z_][a-zA-Z0-9_]*)(\s*)(\()",
                bygroups(Name.Function, Text, Punctuation),
            ),
            # Identifiers (variables, properties)
            (r"[a-zA-Z_][a-zA-Z0-9_]*", Name),
            # Whitespace
            (r"\s+", Text),
            # Catch-all for any other characters
            (r".", Text),
        ]
    }

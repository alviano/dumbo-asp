import pytest
from clingo.ast import Location, Position

from dumbo_asp.utils import one_line, NEW_LINE_SYMBOL, replace_in_parsed_string


@pytest.mark.parametrize("lines", [
    "a\nb\nc",
    "a\nb\n\n\nc",
    "a\n\nb\n\tc",
])
def test_one_line(lines):
    assert one_line(lines).split(NEW_LINE_SYMBOL) == lines.split('\n')


def test_replace_in_parsed_string():
    rule = """
a | re
place
me :- body.
    """.strip()
    location = Location(begin=Position('<string>', line=1, column=5), end=Position('<string>', line=3, column=3))
    assert replace_in_parsed_string(rule, location, "b") == "a | b :- body."

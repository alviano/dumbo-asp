import pytest

from dumbo_asp.primitives.parsers import Parser


def test_parser_error():
    with pytest.raises(Parser.Error) as err:
        Parser.parse_ground_term("\"a\nb")
    assert err.value.line == 1


@pytest.mark.parametrize("program", [
    "a",
    "a : -- b.",
    "a\n\n : --\n\n b.",
])
def test_parse_invalid_program(program):
    with pytest.raises(ValueError):
        Parser.parse_program(program)

from uuid import uuid4
from pathlib import Path
from typing import Final

import clingo.ast
import typeguard

PROJECT_ROOT: Final = Path(__file__).parent.parent
NEW_LINE_SYMBOL: Final = '⏎'


@typeguard.typechecked
def extract_parsed_string(string: str, location: clingo.ast.Location) -> str:
    lines = string.split('\n')
    res = []
    if location.begin.line == location.end.line:
        res.append(lines[location.begin.line - 1][location.begin.column - 1:location.end.column - 1])
    else:
        res.append(lines[location.begin.line - 1][location.begin.column - 1:])
        res.extend(lines[location.begin.line:location.end.line - 1])
        res.append(lines[location.end.line - 1][:location.end.column - 1])
    return '\n'.join(line for line in res)


@typeguard.typechecked
def insert_in_parsed_string(addendum: str, string: str, line: int, column: int) -> str:
    lines = string.split('\n')
    lines[line - 1] = lines[line - 1][:column - 1] + addendum + lines[line - 1][column - 1:]
    return '\n'.join(lines)


@typeguard.typechecked
def replace_in_parsed_string(string: str, location: clingo.ast.Location, new_content: str) -> str:
    lines = string.split('\n')
    lines[location.begin.line - 1] = lines[location.begin.line - 1][:location.begin.column - 1] + \
                                     new_content + \
                                     lines[location.end.line - 1][location.end.column - 1:]
    lines = lines[:location.begin.line] + lines[location.end.line:]
    return '\n'.join(line for line in lines)


@typeguard.typechecked
def one_line(string: str) -> str:
    return NEW_LINE_SYMBOL.join(string.split('\n'))


def uuid() -> str:
    return str(uuid4()).replace('-', '_')

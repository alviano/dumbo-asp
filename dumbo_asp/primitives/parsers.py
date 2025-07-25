import dataclasses
import math
from dataclasses import InitVar

import clingo
import clingo.ast
import typeguard
from dumbo_utils.primitives import PrivateKey
from dumbo_utils.validation import validate


@typeguard.typechecked
class Parser:
    @dataclasses.dataclass(frozen=True)
    class Error(ValueError):
        parsed_string: str
        line: int
        begin: int
        end: int
        message: str
        llm_message: str

        key: InitVar[PrivateKey]
        __key = PrivateKey()

        def __post_init__(self, key: PrivateKey):
            self.__key.validate(key)

        @staticmethod
        def parse(error: str, parsed_string: str) -> "Parser.Error":
            parts = error.split(':', maxsplit=3)
            validate("prefix", parts[0], equals="<string>", help_msg="Unexpected source")
            validate("error", parts[3].startswith(" error: "), equals=True, help_msg="Unexpected error")
            begin, end = Parser.parse_range(parts[2])
            return Parser.Error(
                parsed_string=parsed_string,
                line=int(parts[1]),
                begin=begin,
                end=end,
                message=parts[3][len(" error: "):],
                llm_message=Parser.Error.to_llm_str(int(parts[1]), begin, end, parsed_string, parts[3][len(" error: "):]),
                key=Parser.Error.__key,
            )

        def drop(self, *, first: int = 0, last: int = 0) -> "Parser.Error":
            validate("one line", self.line, equals=1, help_msg="Can drop only from one line parsing")
            return Parser.Error(
                parsed_string=self.parsed_string[first:len(self.parsed_string) - last],
                line=self.line,
                begin=self.begin - first,
                end=self.end - first,
                message=self.message,
                key=Parser.Error.__key,
            )

        def __str__(self):
            lines = self.parsed_string.split('\n')
            width = math.floor(math.log10(len(lines))) + 1
            res = [f"Parsing error in line {self.line}, columns {self.begin}-{self.end}"]
            for line_index, the_line in enumerate(lines, start=1):
                res.append(f"{str(line_index).zfill(width)}| {the_line}")
                if line_index == self.line:
                    res.append('>' * width + '| ' + ' ' * (self.begin - 1) + '^' * (self.end - self.begin + 1))
            res.append(f"error: {self.message}")
            return '\n'.join(res)

        @staticmethod
        def to_llm_str(line: int, begin: int, end: int, code: str, message: str) -> str:
            """
            Returns a string representation of the error formatted for a Large Language Model.
            Shows the error line with one line of context before and after, all with line numbers.
            """
            lines = code.split('\n')
            width = math.floor(math.log10(len(lines))) + 1
            context_lines = []
            
            # Add previous line if it exists
            if line > 1:
                context_lines.append(f"{str(line-1).zfill(width)}| {lines[line-2]}")
                
            # Add error line
            context_lines.append(f"{str(line).zfill(width)}| {lines[line-1]}")
            
            # Add next line if it exists
            if line < len(lines):
                context_lines.append(f"{str(line+1).zfill(width)}| {lines[line]}")
            
            return (
                f"There is a syntax error in the given Answer Set Programming (ASP) code.\n"
                f"Error message: {message}\n"
                f"Location: Line {line}, Columns {begin}-{end}\n"
                f"Here is the piece of code with the error:\n"
                f"```\n"
                f"{'\n'.join(context_lines)}\n"
                f"```\n"
                f"Please fix the syntax error in this line."
            )

    @staticmethod
    def parse_range(string: str) -> tuple[int, int]:
        parts = string.split('-', maxsplit=1)
        if len(parts) == 1:
            return int(parts[0]), int(parts[0])
        return int(parts[0]), int(parts[1])

    @staticmethod
    def parse_ground_term(string: str) -> clingo.Symbol:
        try:
            return clingo.parse_term(string)
        except RuntimeError as err:
            raise Parser.Error.parse(str(err), string)

    @staticmethod
    def parse_program(string: str) -> list[clingo.ast.AST]:
        def callback(ast):
            callback.res.append(ast)
        callback.res = []

        messages = []
        try:
            clingo.ast.parse_string(string, callback, logger=lambda code, message: messages.append((code, message)))
            validate("nonempty res", callback.res, min_len=1)
            validate("base program", callback.res[0].ast_type == clingo.ast.ASTType.Program and
                     callback.res[0].name == "base" and len(callback.res[0].parameters) == 0, equals=True)
            res = [x for x in callback.res[1:] if x.ast_type != clingo.ast.ASTType.Comment]
            validate("only rules", [x for x in res if x.ast_type != clingo.ast.ASTType.Rule], empty=True)
            return res
        except RuntimeError:
            errors = [message[1] for message in messages if message[0] == clingo.MessageCode.RuntimeError]
            validate("errors", messages, length=1)
            raise Parser.Error.parse(errors[0], string)


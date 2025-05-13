from dumbo_asp.primitives.models import Model
from dumbo_asp.primitives.programs import SymbolicProgram
from dumbo_asp.primitives.templates import Template


def test_latin_square():
    program = SymbolicProgram.parse("""
row(1..4).
col(1..4).
value(1..4).

clue((1,1),1).
clue((2,2),1).
clue((3,3),1).
clue((4,4),1).

clue((1,2),2).
clue((2,3),2).
clue((3,4),2).
clue((4,1),2).

clue((1,3),3).
%clue((2,4),3).
clue((3,1),3).
clue((4,2),3).

clue((1,4),4).
clue((2,1),4).
clue((3,2),4).
clue((4,3),4).

__apply_template__("@dumbo/latin square").
    """)
    program = Template.expand_program(program)
    model = [str(atom) for atom in Model.of_program(program) if str(atom).startswith('assign')]
    assert "assign((2,4),3)" in model


def test_sudoku():
    program = SymbolicProgram.parse("""
size(9).
value(1..9).

clue((1,1),5).  clue((1,2),3).                  clue((1,5),7).
clue((2,1),6).  clue((2,4),1).  clue((2,5),9).  clue((2,6),5).
clue((3,2),9).  clue((3,3),8).                  clue((3,8),6).

clue((4,1),8).  clue((4,5),6).  clue((4,9),3).
clue((5,1),4).  clue((5,4),8).  clue((5,6),3).  clue((5,9),1).
clue((6,1),7).  clue((6,5),2).  clue((6,9),6).

clue((7,2),6).                                  clue((7,7),2).  clue((7,8),8).
clue((8,4),4).  clue((8,5),1).  clue((8,6),9).  clue((8,9),5).
clue((9,5),8).                  clue((9,8),7).  clue((9,9),9).

__apply_template__("@dumbo/sudoku").
    """)
    program = Template.expand_program(program)
    model = [str(atom) for atom in Model.of_program(program) if str(atom).startswith('assign')]
    assert "assign((1,3),4)" in model


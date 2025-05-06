__template__("@dumbo/generate grid").
    __doc__("Generate a `grid/2` from `row/1` and `col/1`.").
    grid(Row,Col) :- row(Row), col(Col).
__end__.

__template__("@dumbo/guess grid values").
    __doc__("Guess an assignment (`assign/3`) of values (`value/1`) for cells of a grid (`grid/2).").
    {assign(Row,Col,Value) : value(Value)} = 1 :- grid(Row, Col).
__end__.

__template__("@dumbo/enforce clues in grid").
    __doc__("Verify that the given clues (`clue/3`) are assigned (`assign/3`) correctly.").

    :- clue(Row,Col,Value), not assign(Row,Col,Value).
__end__.

__template__("@dumbo/latin square").
    __doc__(
        "Guess a Latin Square.",
        "The grid is obtained from rows and columns in `row/1` and `col/1`, and the guessed values (from `value/1`) are stored in `assign/3`."
    ).

    __apply_template__("@dumbo/generate grid", (grid, __grid)).
    __apply_template__("@dumbo/guess grid values", (grid, __grid)).
    __apply_template__("@dumbo/enforce clues in grid").
    :- assign(Row,Col,Value), assign(Row',Col,Value), Row < Row'.
    :- assign(Row,Col,Value), assign(Row,Col',Value), Col < Col'.
__end__.

__template__("@dumbo/sudoku").
    __doc__(
        "Guess a Sudoku solution.",
        "The grid of the Sudoku is determined by the rows and columns in `row/1` and `col/1`, and the assignable values from `value/1`.",
        "The produced solution is stored in `assign/3`."
    ).

    __apply_template__("@dumbo/latin square").

    __size(X) :- X = #max{Row : row(Row)}.
    __square(X) :- X = 1..Size, __size(Size), Size == X * X.
    __block((Row', Col'), (Row, Col)) :- Row = 1..Size; Col = 1..Size; Row' = (Row-1) / S; Col' = (Col-1) / S, __size(Size), __square(S).
    :- __block(Block, (Row, Col)), __block(Block, (Row', Col')), (Row, Col) < (Row', Col');
        assign(Row,Col,Value), assign(Row',Col',Value).
__end__.

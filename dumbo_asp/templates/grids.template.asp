__template__("@dumbo/generate grid").
    __doc__("Generate `grid/2`, `row/1` and `col/1` from `rows/1` and `cols/1`.").
    __doc__("There must be exactly one instance of `rows/1` and `cols/1`.").
    __doc__("Rows and columns are 1-indexed.").

    __apply_template__("@dumbo/debug expected exactly one instance (arity 1)", (predicate, rows)).
    __apply_template__("@dumbo/debug expected exactly one instance (arity 1)", (predicate, cols)).

    row(1..Rows) :- rows(Rows).
    col(1..Cols) :- cols(Cols).
    grid(Row,Col) :- row(Row), col(Col).
__end__.

__template__("@dumbo/guess grid values").
    __doc__("Guess an assignment (`assign/2`) of values (`value/1`) for cells of a grid (`grid/2).").

    __apply_template__("@dumbo/debug expected some instances (arity 1)", (predicate, value)).
    __apply_template__("@dumbo/debug expected some instances (arity 2)", (predicate, grid)).

    {assign((Row,Col),Value) : value(Value)} = 1 :- grid(Row, Col).
__end__.

__template__("@dumbo/enforce clues in assign").
    __doc__("Verify that the given clues (`clue/2`) are assigned (`assign/2`) correctly.").

    __apply_template__("@dumbo/debug expected some instances (arity 2)", (predicate, assign)).

    :- clue((Row,Col),Value), not assign((Row,Col),Value).
__end__.

__template__("@dumbo/latin square").
    __doc__(
        "Guess a Latin Square of size given by `size/1`, using values from `value/1` and satisfying the clues in `clue/2`.",
        "The guessed Latin Square is stored in `assign/2`."
    ).

    __apply_template__("@dumbo/debug expected exactly one instance (arity 1)", (predicate, size)).
    __apply_template__("@dumbo/debug expected some instances (arity 1)", (predicate, value)).

    __apply_template__("@dumbo/generate grid", (grid, __grid), (rows, size), (cols, size)).
    __apply_template__("@dumbo/guess grid values", (grid, __grid)).
    __apply_template__("@dumbo/enforce clues in assign").
    :- assign((Row,Col),Value), assign((Row',Col),Value), Row < Row'.
    :- assign((Row,Col),Value), assign((Row,Col'),Value), Col < Col'.
__end__.

__template__("@dumbo/sudoku").
    __doc__(
        "Guess a Sudoku solution of size given by `size/1`, using values from `value/1` and satisfying the clues in `clue/2`.",
        "The produced solution is stored in `assign/2`."
    ).

    __apply_template__("@dumbo/debug expected exactly one instance (arity 1)", (predicate, size)).
    __apply_template__("@dumbo/debug expected some instances (arity 1)", (predicate, value)).

    __square(X) :- X = 1..Size, size(Size), Size == X * X.
    __apply_template__("@dumbo/debug expected exactly one instance (arity 1)", (predicate, __square)).

    __apply_template__("@dumbo/latin square").

    __block((Row', Col'), (Row, Col)) :- Row = 1..Size; Col = 1..Size; Row' = (Row-1) / S; Col' = (Col-1) / S, size(Size), __square(S).
    :- __block(Block, Cell), __block(Block, Cell'), Cell < Cell';
        assign(Cell,Value), assign(Cell',Value).
__end__.

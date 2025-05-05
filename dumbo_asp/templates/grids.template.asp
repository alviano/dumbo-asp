__template__("@dumbo/generate grid").
    grid(Row,Col) :- row(Row), col(Col).
__end__.

__template__("@dumbo/guess grid values").
    {assign(Row,Col,Value) : value(Value)} = 1 :- grid(Row, Col).
__end__.

__template__("@dumbo/enforce clues in grid").
    :- clue(Row,Col,Value), not assign(Row,Col,Value).
__end__.

__template__("@dumbo/latin square").
    __apply_template__("@dumbo/generate grid").
    __apply_template__("@dumbo/guess grid values").
    __apply_template__("@dumbo/enforce clues in grid").
    :- assign(Row,Col,Value), assign(Row',Col,Value), Row < Row'.
    :- assign(Row,Col,Value), assign(Row,Col',Value), Col < Col'.
__end__.

__template__("@dumbo/sudoku").
    __apply_template__("@dumbo/latin square").

    __size(X) :- X = #max{Row : row(Row)}.
    __square(X) :- X = 1..Size, __size(Size), Size == X * X.
    __block((Row', Col'), (Row, Col)) :- Row = 1..Size; Col = 1..Size; Row' = (Row-1) / S; Col' = (Col-1) / S, __size(Size), __square(S).
    :- __block(Block, (Row, Col)), __block(Block, (Row', Col')), (Row, Col) < (Row', Col');
        assign(Row,Col,Value), assign(Row',Col',Value).
__end__.

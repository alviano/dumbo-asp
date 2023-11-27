__template__("@dumbo/symmetric closure").
    closure(X,Y) :- relation(X,Y).
    closure(X,Y) :- relation(Y,X).
__end__.

__template__("@dumbo/symmetric closure guaranteed").
    __apply_template__("@dumbo/symmetric closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/transitive closure").
    closure(X,Y) :- relation(X,Y).
    closure(X,Z) :- closure(X,Y), relation(Y,Z).
__end__.

__template__("@dumbo/transitive closure guaranteed").
    __apply_template__("@dumbo/transitive closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

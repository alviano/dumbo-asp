    __template__("@dumbo/reflexive closure").
    closure(X,X) :- element(X).
    closure(X,Y) :- relation(X,Y).
__end__.

__template__("@dumbo/reflexive closure guaranteed").
    __apply_template__("@dumbo/reflexive closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

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

% removes XY if YX is also in the relation
__template__("@dumbo/antisymmetric closure").
    closure(X,Y) :- relation(X,Y), not relation(Y,X).
    closure(X,X) :- relation(X,X).
__end__.

__template__("@dumbo/equivalence closure").
    __apply_template__("@dumbo/reflexive closure").
    __apply_template__("@dumbo/symmetric closure").
    __apply_template__("@dumbo/transitive closure").
__end__.

__template__("@dumbo/equivalence closure guaranteed").
    __apply_template__("@dumbo/equivalence closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/inverse relation").
    inverse(Y,X) :- relation(X,Y).
__end__.

__template__("@dumbo/inverse relation guaranteed").
    __apply_template__("@dumbo/inverse relation", (inverse, __inverse)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __inverse), (output, inverse)).
__end__.

__template__("@dumbo/relation composition").
    composed(X,Z) :- relation(X,Y), relation(Y,Z).
__end__.

__template__("@dumbo/relation composition guaranteed").
    __apply_template__("@dumbo/relation composition", (composed, __composed)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __composed), (output, composed)).
__end__.

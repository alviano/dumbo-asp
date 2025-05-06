__template__("@dumbo/reflexive closure").
    __doc__("Compute the reflexive closure (in `closure/2`) of the relation encoded by predicates `element/1` and `relation/2`.").

    closure(X,X) :- element(X).
    closure(X,Y) :- relation(X,Y).
__end__.

__template__("@dumbo/reflexive closure guaranteed").
    __doc__(
        "Compute the reflexive closure (in `closure/2`) of the relation encoded by predicates `element/1` and `relation/2`.",
        "If the `closure/2` predicate is altered by other rules in the program, a __debug__ atom is produced."
    ).

    __apply_template__("@dumbo/reflexive closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/symmetric closure").
    __doc__("Compute the symmetric closure (in `closure/2`) of the relation encoded by predicates `relation/2`.").

    closure(X,Y) :- relation(X,Y).
    closure(X,Y) :- relation(Y,X).
__end__.

__template__("@dumbo/symmetric closure guaranteed").
    __doc__(
        "Compute the symmetric closure (in `closure/2`) of the relation encoded by predicates `relation/2`.",
        "If the `closure/2` predicate is altered by other rules in the program, a __debug__ atom is produced."
    ).

    __apply_template__("@dumbo/symmetric closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/transitive closure").
    __doc__("Compute the transitive closure (in `closure/2`) of the relation encoded by predicates `relation/2`.").

    closure(X,Y) :- relation(X,Y).
    closure(X,Z) :- closure(X,Y), relation(Y,Z).
__end__.

__template__("@dumbo/transitive closure guaranteed").
    __doc__(
        "Compute the transitive closure (in `closure/2`) of the relation encoded by predicates `relation/2`.",
        "If the `closure/2` predicate is altered by other rules in the program, a __debug__ atom is produced."
    ).

    __apply_template__("@dumbo/transitive closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/antisymmetric closure").
    __doc__(
        "Remove XY if YX is also in the relation encoded by predicate `relation/2`.",
        "The new relation is stored in predicate `closure/2`."
    ).

    closure(X,Y) :- relation(X,Y), not relation(Y,X).
    closure(X,X) :- relation(X,X).
__end__.

__template__("@dumbo/equivalence closure").
    __doc__("Compute the equivalence closure (in `closure/2`) of the relation encoded by predicates `element/1` and `relation/2`.").

    __apply_template__("@dumbo/reflexive closure").
    __apply_template__("@dumbo/symmetric closure").
    __apply_template__("@dumbo/transitive closure").
__end__.

__template__("@dumbo/equivalence closure guaranteed").
    __doc__(
        "Compute the equivalence closure (in `closure/2`) of the relation encoded by predicates `element/1` and `relation/2`.",
        "If the `closure/2` predicate is altered by other rules in the program, a __debug__ atom is produced."
    ).

    __apply_template__("@dumbo/equivalence closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/inverse relation").
    __doc__("Compute the inverse relation (in `inverse/2`) of the relation encoded by predicate `relation/2`.").

    inverse(Y,X) :- relation(X,Y).
__end__.

__template__("@dumbo/inverse relation guaranteed").
    __doc__(
        "Compute the inverse relation (in `inverse/2`) of the relation encoded by predicate `relation/2`.",
        "If the `inverse/2` predicate is altered by other rules in the program, a __debug__ atom is produced."
    ).

    __apply_template__("@dumbo/inverse relation", (inverse, __inverse)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __inverse), (output, inverse)).
__end__.

__template__("@dumbo/relation composition").
    __doc__("Compute the relation composition (in `composed/2`) of the relation encoded by predicate `relation/2`.").

    composed(X,Z) :- relation(X,Y), relation(Y,Z).
__end__.

__template__("@dumbo/relation composition guaranteed").
    __doc__(
        "Compute the relation composition (in `composed/2`) of the relation encoded by predicate `relation/2`.",
        "If the `composed/2` predicate is altered by other rules in the program, a __debug__ atom is produced."
    ).

    __apply_template__("@dumbo/relation composition", (composed, __composed)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __composed), (output, composed)).
__end__.

%*
*** TEMPLATES PRODUCED PROGRAMMATICALLY : BEGIN ***

__template__("@dumbo/exact copy (arity {arity})").
    output({terms}) :- input({terms}).
    :- output({terms}), not input({terms}).
__end__.

__template__("@dumbo/collect arguments (arity {arity})").
    output(X{index}) :- input({terms}).
    ...
 __end__.

__template__("@dumbo/collect argument {index} of {arity}").
    output(X{index}) :- input({terms}).
__end__.

*** TEMPLATES PRODUCED PROGRAMMATICALLY : END ***
*%

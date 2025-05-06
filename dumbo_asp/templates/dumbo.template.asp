%*
*** TEMPLATES PRODUCED PROGRAMMATICALLY : BEGIN ***

__template__("@dumbo/fail if debug messages").
    :- __debug__.
    :- __debug__(X1).
    :- __debug__(X1,X2).
    :- __debug__(X1,X2,X3).
    ...
__end__.

__template__("@dumbo/exact copy (arity {arity})").
    __doc__("Copy `input/{arity}` in `output/{arity}`, and generates `__debug__` atoms if `output/{arity}` is altered outside the template.").
    output({terms}) :- input({terms}).
    __debug__("@dumbo/exact copy (arity {arity}): unexpected ", output({terms}), " without ", input({terms})) :- output({terms}), not input({terms}).
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

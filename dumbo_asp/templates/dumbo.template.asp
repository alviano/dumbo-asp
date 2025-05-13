__template__("@dumbo/init").
    __doc__("Define symbols to avoid some clingo warnings.").
    __debug_off__ :- #false.
__end__.

__template__("@dumbo/debug off").
    __doc__("Bodies of rules with atomic `__debug__/*` heads are injected with `not __debug_off__` so to essentially not evaluate them (in production) when this template is applied.").
    __debug_off__.
__end__.

%*
*** TEMPLATES PRODUCED PROGRAMMATICALLY : BEGIN ***

__template__("@dumbo/fail if debug messages").
    :- __debug__.
    :- __debug__(X1).
    :- __debug__(X1,X2).
    :- __debug__(X1,X2,X3).
    ...
__end__.

__template__("@dumbo/debug expected exactly one instance (arity {arity})").
    __doc__("Derive __debug__/* atoms if `predicate/{arity}` does not contain exactly one instance.").
    __debug__("Expecting 1 instance of ", predicate({arity}), ", found ", Count) :- Count = #count{{terms} : predicate({terms})}, Count != 1.
__end__.

__template__("@dumbo/debug expected some instances (arity {arity})").
    __doc__("Derive __debug__/* atoms if `predicate/{arity}` does not contain some instances.").
    __debug__("Expecting some instance of ", predicate({arity}), ", found none") :- #count{{terms} : predicate({terms})} = 0.
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

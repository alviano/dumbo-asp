__template__("@dumbo/subsets").
    __doc__("Add to subset/2 the sets (encoded by set/1 and in_set/2) that are in subset relationship.").
    subset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S') : in_set(X,S).
__end__.

__template__("@dumbo/supersets").
    __doc__("Add to superset/2 the sets (encoded by set/1 and in_set/2) that are in superset relationship.").
    superset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S) : in_set(X,S').
__end__.

__template__("@dumbo/strict subsets").
    __doc__("Add to subset/2 the sets (encoded by set/1 and in_set/2) that are in strict subset relationship.").
    subset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S') : in_set(X,S);
        in_set(X,S'), not in_set(X,S).
__end__.

__template__("@dumbo/strict supersets").
    __doc__("Add to superset/2 the sets (encoded by set/1 and in_set/2) that are in strict superset relationship.").
    superset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S) : in_set(X,S');
        in_set(X,S), not in_set(X,S').
__end__.

__template__("@dumbo/equal sets").
    __doc__("Add to equals/2 the sets (encoded by set/1 and in_set/2) with the same elements.").
    equals(S,S') :- set(S), set(S'), S < S';
        in_set(X,S) : in_set(X,S');
        in_set(X,S') : in_set(X,S).
__end__.

__template__("@dumbo/discard duplicate sets").
    __doc__("Add to unique/1 the sets (encoded by set/1 and in_set/2) that have preceding duplicate (according to natural order of IDs).").
    __apply_template__("@dumbo/equal sets", (equals, __equals)).
    unique(S) :- set(S), not __equals(S,_).
__end__.

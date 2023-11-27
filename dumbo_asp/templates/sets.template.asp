% add to subset/2 the sets (encoded by set/1 and in_set/2) that are in subset relationship
__template__("@dumbo/subsets").
    subset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S') : in_set(X,S).
__end__.

% add to superset/2 the sets (encoded by set/1 and in_set/2) that are in superset relationship
__template__("@dumbo/supersets").
    superset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S) : in_set(X,S').
__end__.

% add to subset/2 the sets (encoded by set/1 and in_set/2) that are in strict subset relationship
__template__("@dumbo/strict subsets").
    subset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S') : in_set(X,S);
        in_set(X,S'), not in_set(X,S).
__end__.

% add to superset/2 the sets (encoded by set/1 and in_set/2) that are in strict superset relationship
__template__("@dumbo/strict supersets").
    superset(S,S') :- set(S), set(S'), S != S';
        in_set(X,S) : in_set(X,S');
        in_set(X,S), not in_set(X,S').
__end__.

% add to equals/2 the sets (encoded by set/1 and in_set/2) with the same elements
__template__("@dumbo/equal sets").
    equals(S,S') :- set(S), set(S'), S < S';
        in_set(X,S) : in_set(X,S');
        in_set(X,S') : in_set(X,S).
__end__.

% add to unique/1 the sets (encoded by set/1 and in_set/2) that have preceding duplicate (according to natural order of IDs)
__template__("@dumbo/discard duplicate sets").
    __apply_template__("@dumbo/equal sets", (equals, __equals)).
    unique(S) :- set(S), not __equals(S,_).
__end__.

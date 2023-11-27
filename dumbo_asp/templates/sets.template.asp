__template__("@dumbo/equal sets").
    equals(S,S') :- set(S), set(S'), S < S';
        in_set(X,S) : in_set(X,S');
        in_set(X,S') : in_set(X,S).
__end__.

__template__("@dumbo/discard duplicate sets").
    __apply_template__("@dumbo/equal sets", (equals, __equals)).
    unique(S) :- set(S), not __equals(S,_).
__end__.

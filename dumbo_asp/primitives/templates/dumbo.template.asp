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


__template__("@dumbo/symmetric closure").
    closure(X,Y) :- relation(X,Y).
    closure(X,Y) :- relation(Y,X).
__end__.

__template__("@dumbo/symmetric closure guaranteed").
    __apply_template__("@dumbo/symmetric closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/reachable nodes").
    reach(X) :- start(X).
    reach(Y) :- reach(X), link(X,Y).
__end__.

__template__("@dumbo/connected graph").
    __start(X) :- X = #min{Y : node(Y)}.
    __apply_template__("@dumbo/reachable nodes", (start, __start), (reach, __reach)).
    :- node(X), not __reach(X).
__end__.

__template__("@dumbo/transitive closure").
    closure(X,Y) :- relation(X,Y).
    closure(X,Z) :- closure(X,Y), relation(Y,Z).
__end__.

__template__("@dumbo/transitive closure guaranteed").
    __apply_template__("@dumbo/transitive closure", (closure, __closure)).
    __apply_template__("@dumbo/exact copy (arity 2)", (input, __closure), (output, closure)).
__end__.

__template__("@dumbo/spanning tree of undirected graph").
    {tree(X,Y) : link(X,Y), X < Y} = C - 1 :- C = #count{X : node(X)}.
    __apply_template__("@dumbo/symmetric closure", (relation, tree), (closure, __tree)).
    __apply_template__("@dumbo/connected graph", (link, __tree)).
__end__.

__template__("@dumbo/all simple directed paths and their length").
    path_length((N,nil),0) :- node(N).
    path_length((N',(N,P)),L+1) :- path_length((N,P),L), max_length(M), L < M, link(N,N'), not in_path(N',P).
    path_length((N',(N,P)),L+1) :- path_length((N,P),L), not max_length(_),    link(N,N'), not in_path(N',P).

    in_path(N,(N,P)) :- path_length((N,P),_).
    in_path(N',(N,P)) :- path_length((N,P),_), in_path(N',P).

    path(P) :- in_path(_,P).
__end__.

__template__("@dumbo/all simple directed paths").
    __apply_template__("@dumbo/all simple directed paths and their length", (path_length, __path_length)).
__end__.

__template__("@dumbo/all simple directed paths of given length").
    __apply_template__("@dumbo/all simple directed paths and their length",
        (max_length, length),
        (path, __path),
        (in_path, __in_path),
        (path_length, __path_length)
    ).

    path(P) :- __path(P), __path_length(P,L), length(L).
    in_path(N,P) :- path(P), __in_path(N,P).
__end__.

__template__("@dumbo/equal sets").
    equals(S,S') :- set(S), set(S'), S < S';
        in_set(X,S) : in_set(X,S');
        in_set(X,S') : in_set(X,S).
__end__.

__template__("@dumbo/discard duplicate sets").
    __apply_template__("@dumbo/equal sets", (equals, __equals)).
    unique(S) :- set(S), not __equals(S,_).
__end__.

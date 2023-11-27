__template__("@dumbo/reachable nodes").
    reach(X) :- start(X).
    reach(Y) :- reach(X), link(X,Y).
__end__.

__template__("@dumbo/connected graph").
    __start(X) :- X = #min{Y : node(Y)}.
    __apply_template__("@dumbo/reachable nodes", (start, __start), (reach, __reach)).
    :- node(X), not __reach(X).
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
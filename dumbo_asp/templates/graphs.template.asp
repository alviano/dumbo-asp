__template__("@dumbo/reachable nodes").
    __doc__(
        "Compute the nodes reached from the node(s) in `start/1`.",
        "Reached nodes are stored in `reach/1`."
    ).

    reach(X) :- start(X).
    reach(Y) :- reach(X), link(X,Y).
__end__.

__template__("@dumbo/connected graph").
    __doc__("Verify that the directed graph encoded by predicates `node/1` and `link/2` is connected (i.e., every node reaches all other nodes).").

    __start(X) :- X = #min{Y : node(Y)}.
    __apply_template__("@dumbo/reachable nodes", (start, __start), (reach, __reach)).
    :- node(X), not __reach(X).
__end__.

__template__("@dumbo/spanning tree of undirected graph").
    __doc__(
        "Guess a spanning tree of the undirected graph encoded by predicates `node/1` and `link/2`.",
        "The spanning tree is encoded by predicate `tree/2."
    ).

    {tree(X,Y) : link(X,Y), X < Y} = C - 1 :- C = #count{X : node(X)}.
    __apply_template__("@dumbo/symmetric closure", (relation, tree), (closure, __tree)).
    __apply_template__("@dumbo/connected graph", (link, __tree)).
__end__.

__template__("@dumbo/all simple directed paths and their length").
    __doc__(
        "Compute all simple paths (no repeating nodes), and their length, of the directed graph encoded by predicates `node/1` and `link/2`.",
        "The length of the paths is bounded by `max_length/1`.",
        "Paths are encoded by predicates `path/1`, `in_path/2` and `path_length/2`."
    ).

    path_length((N,nil),0) :- node(N).
    path_length((N',(N,P)),L+1) :- path_length((N,P),L), max_length(M), L < M, link(N,N'), not in_path(N',P).
    path_length((N',(N,P)),L+1) :- path_length((N,P),L), not max_length(_),    link(N,N'), not in_path(N',P).

    in_path(N,(N,P)) :- path_length((N,P),_).
    in_path(N',(N,P)) :- path_length((N,P),_), in_path(N',P).

    path(P) :- in_path(_,P).
__end__.

__template__("@dumbo/all simple directed paths").
    __doc__(
        "Compute all simple paths (no repeating nodes) of the directed graph encoded by predicates `node/1` and `link/2`.",
        "The length of the paths is bounded by `max_length/1`.",
        "Paths are encoded by predicates `path/1` and `in_path/2`."
    ).

    __apply_template__("@dumbo/all simple directed paths and their length", (path_length, __path_length)).
__end__.

__template__("@dumbo/all simple directed paths of given length").
    __doc__(
        "Compute all simple paths (no repeating nodes) of the directed graph encoded by predicates `node/1` and `link/2`.",
        "The length of the paths is fixed to `length/1`.",
        "Paths are encoded by predicates `path/1` and `in_path/2`."
    ).

    __apply_template__("@dumbo/all simple directed paths and their length",
        (max_length, length),
        (path, __path),
        (in_path, __in_path),
        (path_length, __path_length)
    ).

    path(P) :- __path(P), __path_length(P,L), length(L).
    in_path(N,P) :- path(P), __in_path(N,P).
__end__.

__template__("@dumbo/cycle detection").
    __doc__("Detect cycles in the graph encoded by predicate `link/2`.").
    __doc__("Nodes involved in the detected cycles are stored in predicate `cycle/1`.").

    cycle(X) :- link(X,Y), __path(Y,X).
    __path(X,Y) :- link(X,Y).
    __path(X,Z) :- link(X,Y), __path(Y,Z).
__end__.

__template__("@dumbo/strongly connected components").
    __doc__(
        "Compute the strongly connected components (SCCs) of the graph encoded by predicates `node/1` and `link/2`.",
        "SCCs are encoded by predicates `scc/1` and `in_scc/2`.",
        "The ID of every SCC is the smallest ID (according to their natural ordering) of the node in the SCC."
    ).

    __apply_template__("@dumbo/transitive closure", (relation, link), (closure, __reach)).
    __same_scc(X,Y) :- __reach(X,Y), __reach(Y,X).
    __same_scc(X,X) :- node(X).

    in_scc(X,ID) :- node(X), ID = #min{Y : __same_scc(X,Y)}.
    scc(ID) :- in_scc(X,ID).
__end__.

from deepsynth.pcfg import PCFG

from collections import deque


def dfs(G : PCFG):
    '''
    A generator that enumerates all programs using a DFS.
    '''

    # We need to reverse the rules:
    new_rules = {}
    for S in G.rules:
        new_rules[S] = {}
        sorted_derivation_list = sorted(
            G.rules[S], key=lambda P: G.rules[S][P][1]
        )
        for P in sorted_derivation_list:
            new_rules[S][P] = G.rules[S][P]
    G = PCFG(start = G.start, 
        rules = new_rules, 
        max_program_depth = G.max_program_depth)

    frontier = deque()
    initial_non_terminals = deque()
    initial_non_terminals.append(G.start)
    frontier.append((None, initial_non_terminals))
    # A frontier is a queue of pairs (partial_program, non_terminals) describing a partial program:
    # partial_program is the list of primitives and variables describing the leftmost derivation, and
    # non_terminals is the queue of non-terminals appearing from left to right

    while len(frontier) != 0:
        partial_program, non_terminals = frontier.pop()
        if len(non_terminals) == 0: 
            yield partial_program
        else:
            S = non_terminals.pop()
            for P in G.rules[S]:
                args_P, w = G.rules[S][P]
                new_partial_program = (P, partial_program)
                new_non_terminals = non_terminals.copy()
                for arg in args_P:
                    new_non_terminals.append(arg)
                frontier.append((new_partial_program, new_non_terminals))

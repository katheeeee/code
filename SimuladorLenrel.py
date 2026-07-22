from itertools import count


class RegexNFA:
    def __init__(self):
        self.transitions = {}
        self.counter = count()

    def new_state(self):
        s = next(self.counter)
        self.transitions[s] = {}
        return s

    def add_transition(self, src, symbol, dst):
        self.transitions[src].setdefault(symbol, set()).add(dst)

    def parse(self, regex):
        self.pos = 0
        self.regex = regex
        start, accept = self.parse_expr()
        if self.pos != len(regex):
            raise ValueError(f'Símbolo inesperado en posición {self.pos}')
        return start, accept

    def peek(self):
        return self.regex[self.pos] if self.pos < len(self.regex) else None

    def consume(self, ch=None):
        c = self.peek()
        if ch and c != ch:
            raise ValueError(f"Se esperaba '{ch}' en posición {self.pos}")
        self.pos += 1
        return c

    def parse_expr(self):
        start, accept = self.parse_term()
        while self.peek() == '|':
            self.consume('|')
            s2, a2 = self.parse_term()
            new_start = self.new_state()
            new_accept = self.new_state()
            self.add_transition(new_start, '', start)
            self.add_transition(new_start, '', s2)
            self.add_transition(accept, '', new_accept)
            self.add_transition(a2, '', new_accept)
            start, accept = new_start, new_accept
        return start, accept

    def parse_term(self):
        start, accept = self.parse_factor()
        while self.peek() is not None and self.peek() not in '|)':
            s2, a2 = self.parse_factor()
            self.add_transition(accept, '', s2)
            accept = a2
        return start, accept

    def parse_factor(self):
        start, accept = self.parse_base()
        while self.peek() in ('*', '+', '?'):
            op = self.consume()
            if op == '*':
                new_start = self.new_state()
                new_accept = self.new_state()
                self.add_transition(new_start, '', start)
                self.add_transition(new_start, '', new_accept)
                self.add_transition(accept, '', start)
                self.add_transition(accept, '', new_accept)
                start, accept = new_start, new_accept
            elif op == '+':
                new_accept = self.new_state()
                self.add_transition(accept, '', start)
                self.add_transition(accept, '', new_accept)
                accept = new_accept
            elif op == '?':
                new_start = self.new_state()
                new_accept = self.new_state()
                self.add_transition(new_start, '', start)
                self.add_transition(new_start, '', new_accept)
                self.add_transition(accept, '', new_accept)
                start, accept = new_start, new_accept
        return start, accept

    def parse_base(self):
        c = self.peek()
        if c == '(':
            self.consume('(')
            start, accept = self.parse_expr()
            self.consume(')')
            return start, accept
        self.consume()
        start = self.new_state()
        accept = self.new_state()
        self.add_transition(start, c, accept)
        return start, accept


def epsilon_closure(transitions, states):
    stack = list(states)
    closure = set(states)
    while stack:
        state = stack.pop()
        for nxt in transitions.get(state, {}).get('', set()):
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return frozenset(closure)


def move(transitions, states, symbol):
    result = set()
    for state in states:
        result.update(transitions.get(state, {}).get(symbol, set()))
    return result


def get_alphabet(transitions):
    symbols = set()
    for trans in transitions.values():
        for symbol in trans:
            if symbol != '':
                symbols.add(symbol)
    return symbols


def subset_construction(transitions, nfa_start, nfa_accept):
    alphabet = get_alphabet(transitions)
    start = epsilon_closure(transitions, {nfa_start})
    dfa_states = {start}
    dfa_transitions = {}
    unmarked = [start]
    while unmarked:
        current = unmarked.pop()
        dfa_transitions[current] = {}
        for symbol in alphabet:
            moved = move(transitions, current, symbol)
            target = epsilon_closure(transitions, moved)
            if not target:
                continue
            dfa_transitions[current][symbol] = target
            if target not in dfa_states:
                dfa_states.add(target)
                unmarked.append(target)
    dfa_accept = {s for s in dfa_states if nfa_accept in s}
    return dfa_states, dfa_transitions, start, dfa_accept, alphabet


def minimize_dfa(states, transitions, start, accept, alphabet):
    non_accept = set(states) - accept
    partitions = [p for p in (accept, non_accept) if p]
    changed = True
    while changed:
        changed = False
        new_partitions = []
        for group in partitions:
            buckets = {}
            for state in group:
                signature = []
                for symbol in alphabet:
                    target = transitions.get(state, {}).get(symbol)
                    group_index = next((i for i, g in enumerate(partitions) if target in g), -1)
                    signature.append(group_index)
                buckets.setdefault(tuple(signature), set()).add(state)
            new_partitions.extend(buckets.values())
        if len(new_partitions) != len(partitions):
            changed = True
        partitions = new_partitions

    state_to_group = {}
    for i, group in enumerate(partitions):
        for state in group:
            state_to_group[state] = i

    min_transitions = {}
    for i, group in enumerate(partitions):
        representative = next(iter(group))
        min_transitions[i] = {}
        for symbol in alphabet:
            target = transitions.get(representative, {}).get(symbol)
            if target is not None:
                min_transitions[i][symbol] = state_to_group[target]

    min_start = state_to_group[start]
    min_accept = {state_to_group[s] for s in accept}
    min_states = set(range(len(partitions)))
    return min_states, min_transitions, min_start, min_accept


class RegexSimulator:
    def __init__(self, regex):
        self.regex = regex
        parser = RegexNFA()
        nfa_start, nfa_accept = parser.parse(regex)
        dfa_states, dfa_transitions, dfa_start, dfa_accept, alphabet = subset_construction(parser.transitions, nfa_start, nfa_accept)
        self.states, self.transitions, self.start, self.accept = minimize_dfa(dfa_states, dfa_transitions, dfa_start, dfa_accept, alphabet)

    def match(self, string):
        current = self.start
        for ch in string:
            if ch not in self.transitions.get(current, {}):
                return False
            current = self.transitions[current][ch]
        return current in self.accept

    def graficar(self):
        import networkx as nx
        import matplotlib.pyplot as plt

        G = nx.MultiDiGraph()
        for estado in self.states:
            G.add_node(estado)
        for origen, trans in self.transitions.items():
            for simbolo, destino in trans.items():
                G.add_edge(origen, destino, label=simbolo)

        pos = nx.spring_layout(G, seed=7, k=1.5)
        plt.figure(figsize=(7, 6))
        colores = []
        for estado in G.nodes():
            if estado in self.accept:
                colores.append('#90EE90')
            elif estado == self.start:
                colores.append('#87CEFA')
            else:
                colores.append('#D3D3D3')
        nx.draw(G, pos, with_labels=True, node_color=colores, node_size=1600,
                 font_size=12, font_weight='bold', arrowsize=20,
                 connectionstyle='arc3,rad=0.15')
        edge_labels = {}
        for u, v, d in G.edges(data=True):
            key = (u, v)
            etiqueta = d['label']
            edge_labels[key] = etiqueta if key not in edge_labels else edge_labels[key] + ',' + etiqueta
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=11)
        plt.title(f'AFD minimizado para: {self.regex}')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(f'afd_{self.regex}.png'.replace('|', '_').replace('*', '_').replace('(', '').replace(')', '').replace('+', '_').replace('?', '_'), dpi=150)
        plt.show()


if __name__ == '__main__':
    casos = [
        ('(a|b)*abb', ['abb', 'aabb', 'babb', 'ab', 'abbb', 'aaabb']),
        ('a*b+', ['b', 'ab', 'aab', 'aaabbb', 'a', '']),
        ('(ab)*', ['', 'ab', 'abab', 'aba', 'a']),
        ('0|1(0|1)*', ['0', '1', '101', '110', '', '01']),
        ('c(a|d)*r', ['car', 'cr', 'cadar', 'cadr', 'ca']),
    ]
    for regex, pruebas in casos:
        print(f'Expresión regular: {regex}')
        sim = RegexSimulator(regex)
        print(f'  Estados en el AFD minimizado: {len(sim.states)}')
        for cadena in pruebas:
            resultado = 'ACEPTA' if sim.match(cadena) else 'RECHAZA'
            print(f'  "{cadena}" -> {resultado}')
        sim.graficar()
        print()

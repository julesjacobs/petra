#!/usr/bin/env python3
"""Independent positive-witness checking against the original LoLA source.

No converter/parser code is imported. This checker never certifies negatives.
Use the companion driver for process-level memory and wall limits.
"""
import hashlib
import json
import math
from pathlib import Path
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Budget:
    def __init__(self, max_work=200_000_000, deadline=None):
        require(type(max_work) is int and max_work >= 0, 'invalid checker work limit')
        self.remaining = max_work
        self.deadline = deadline

    def tick(self, work=1):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise TimeoutError('source checker time limit')
        self.remaining -= work
        if self.remaining < 0:
            raise TimeoutError('source checker work limit')


def natural(text):
    require(bool(text) and all('0' <= c <= '9' for c in text), 'expected natural number')
    return int(text)


def parse_lola(text, budget):
    budget.tick(len(text))
    statements = text.split(';')
    require(len(statements) >= 3 and not statements[-1].strip(), 'missing LoLA terminator')
    first, second = statements[:2]

    def body(statement, keyword):
        words = statement.strip().split(None, 1)
        require(words and words[0] == keyword, f'expected {keyword}')
        return words[1] if len(words) == 2 else ''

    places = [name.strip() for name in body(first, 'PLACE').split(',')]
    require(all(places) and len(set(places)) == len(places), 'duplicate or empty source place')
    require(all(not any(c.isspace() for c in name) for name in places), 'whitespace in source place')
    known = set(places)

    def marking(text):
        values = {}
        if not text.strip():
            return values
        for term in text.split(','):
            budget.tick(len(term) + 1)
            name, separator, number = term.strip().rpartition(':')
            name, number = name.strip(), number.strip()
            require(separator and name in known and name not in values, 'unknown or duplicate source arc place')
            values[name] = natural(number)
        return values

    initial = dict.fromkeys(places, 0)
    initial.update(marking(body(second, 'MARKING')))
    transitions = {}
    rest = statements[2:-1]
    require(len(rest) % 2 == 0, 'incomplete transition')
    for index in range(0, len(rest), 2):
        budget.tick()
        lines = rest[index].strip().splitlines()
        require(len(lines) >= 2, 'missing transition header or consume line')
        name = body(lines[0], 'TRANSITION').strip()
        require(name and name not in transitions, 'duplicate or empty source transition')
        pre = marking(body('\n'.join(lines[1:]), 'CONSUME'))
        post = marking(body(rest[index + 1], 'PRODUCE'))
        transitions[name] = (pre, post)
    budget.tick()
    return places, initial, transitions


class Formula:
    def __init__(self, text, places, budget):
        self.text, self.places, self.budget = text, set(places), budget
        self.position = 0
        budget.tick(len(text))
        self.word('EF')
        self.symbol('(')
        self.tree = self.disjunction(0)
        self.symbol(')')
        self.space()
        require(self.position == len(text), 'syntax outside EF operand')

    def space(self):
        while self.position < len(self.text) and self.text[self.position].isspace():
            self.position += 1

    def symbol(self, symbol):
        self.space()
        require(self.text.startswith(symbol, self.position), f'expected {symbol}')
        self.position += len(symbol)

    def peek_word(self, word):
        self.space()
        end = self.position + len(word)
        return self.text.startswith(word, self.position) and (end == len(self.text) or self.text[end].isspace() or self.text[end] in '()')

    def word(self, word):
        require(self.peek_word(word), f'expected {word}')
        self.position += len(word)

    def disjunction(self, depth):
        terms = [self.conjunction(depth)]
        while self.peek_word('OR'):
            self.word('OR')
            terms.append(self.conjunction(depth))
        return ('or', terms)

    def conjunction(self, depth):
        terms = [self.factor(depth)]
        while self.peek_word('AND'):
            self.word('AND')
            terms.append(self.factor(depth))
        return ('and', terms)

    def factor(self, depth):
        self.budget.tick()
        require(depth <= 256, 'formula depth limit')
        self.space()
        require(self.position < len(self.text), 'truncated formula')
        if self.text[self.position] == '(':
            self.position += 1
            node = self.disjunction(depth + 1)
            self.symbol(')')
            return node
        start = self.position
        while self.position < len(self.text) and not self.text[self.position].isspace() and self.text[self.position] not in '()=<>':
            self.position += 1
        name = self.text[start:self.position]
        require(name in self.places, 'unknown source target place')
        self.space()
        if self.text.startswith('>=', self.position):
            self.position += 2
            operator = '>='
        else:
            self.symbol('=')
            operator = '='
        self.space()
        start = self.position
        while self.position < len(self.text) and '0' <= self.text[self.position] <= '9':
            self.position += 1
        value = natural(self.text[start:self.position])
        return ('atom', name, operator, value)

    def accepts(self, marking):
        def evaluate(node):
            self.budget.tick()
            if node[0] == 'atom':
                _, name, operator, count = node
                return marking[name] == count if operator == '=' else marking[name] >= count
            values = [evaluate(child) for child in node[1]]
            return all(values) if node[0] == 'and' else any(values)
        return evaluate(self.tree)


def validate_mapping(source, mapping, canonical, budget):
    places, initial, transitions = source
    require(type(mapping) is dict and set(mapping) == {'places', 'transitions'}, 'invalid mapping object')
    for field, expected in [('places', places), ('transitions', transitions)]:
        actual = mapping[field]
        budget.tick(len(expected))
        require(type(actual) is list and all(type(name) is str for name in actual), 'invalid mapping names')
        require(len(actual) == len(expected) and len(set(actual)) == len(actual) and set(actual) == set(expected), 'mapping is not a source bijection')
    require(type(canonical) is dict and canonical.get('places') == [f'p{i}' for i in range(len(places))], 'canonical place IDs mismatch')
    require(type(canonical.get('initial')) is list and all(type(n) is int and n >= 0 for n in canonical['initial']), 'invalid canonical initial marking')
    require(canonical['initial'] == [initial[name] for name in mapping['places']], 'canonical initial marking differs from source')
    require(type(canonical.get('transitions')) is list and len(canonical['transitions']) == len(transitions), 'canonical transition count mismatch')
    for index, name in enumerate(mapping['transitions']):
        budget.tick()
        transition = canonical['transitions'][index]
        require(type(transition) is dict and transition.get('name') == f't{index}', 'canonical transition ID mismatch')
        for field, expected in zip(('pre', 'post'), transitions[name]):
            arcs = transition.get(field)
            require(type(arcs) is list, 'invalid canonical arc list')
            actual = {}
            for arc in arcs:
                budget.tick()
                require(type(arc) is list and len(arc) == 2, 'invalid canonical arc')
                place, weight = arc
                require(type(place) is int and 0 <= place < len(places) and type(weight) is int and weight > 0, 'invalid canonical arc index or weight')
                original = mapping['places'][place]
                require(original not in actual, 'duplicate canonical arc')
                actual[original] = weight
            require(actual == {p: n for p, n in expected.items() if n != 0}, 'canonical weighted arcs differ from source')
    budget.tick()


def replay(lola, formula, mapping, canonical, outcome, *, max_work=200_000_000, deadline=None):
    budget = Budget(max_work, deadline)
    source = parse_lola(lola, budget)
    target = Formula(formula, source[0], budget)
    validate_mapping(source, mapping, canonical, budget)
    require(type(outcome) is dict and outcome.get('verdict') == 'reachable', 'source replay requires a positive proposal')
    trace = outcome.get('trace')
    require(type(trace) is list, 'invalid trace')
    current = source[1].copy()
    for step in trace:
        budget.tick()
        require(type(step) is int and 0 <= step < len(mapping['transitions']), 'invalid witness transition ID')
        pre, post = source[2][mapping['transitions'][step]]
        for name, weight in pre.items():
            budget.tick()
            require(current[name] >= weight, 'source transition disabled')
        for name, weight in pre.items():
            budget.tick()
            current[name] -= weight
        for name, weight in post.items():
            budget.tick()
            current[name] += weight
    require(target.accepts(current), 'source formula rejects final marking')
    expected = [current[name] for name in mapping['places']]
    if outcome.get('marking') is not None:
        claimed = outcome['marking']
        require(type(claimed) is list and all(type(n) is int and n >= 0 for n in claimed), 'invalid claimed marking')
        require(claimed == expected, 'claimed final marking differs from source replay')
    budget.tick()
    return {'verdict': 'reachable', 'independent_check': 'python-original-lola-witness', 'steps': len(trace),
            'source_formula_satisfied': True, 'mapping_check': 'bijective-and-canonical-net-exact',
            'arithmetic': 'python-arbitrary-precision', 'marking': expected}


class Files:
    def __init__(self, max_bytes, deadline):
        self.max_bytes, self.deadline = max_bytes, deadline
        self.identities = {}

    @staticmethod
    def identity(path):
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns

    def read(self, path, sha256=None):
        path = Path(path).resolve()
        before = self.identity(path)
        require(path not in self.identities or self.identities[path] == before, 'source checker input mutated between reads')
        require(before[2] <= self.max_bytes, 'source checker file size limit')
        blocks = []
        size = 0
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while True:
                if time.monotonic() >= self.deadline:
                    raise TimeoutError('source checker time limit')
                block = stream.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                require(size <= self.max_bytes, 'source checker file size limit')
                digest.update(block)
                blocks.append(block)
        require(self.identity(path) == before, 'source checker input mutated')
        require(sha256 is None or digest.hexdigest() == sha256, 'source checker SHA256 mismatch')
        self.identities[path] = before
        return b''.join(blocks)

    def unchanged(self):
        for path, identity in self.identities.items():
            require(self.identity(path) == identity, 'source checker input mutated')


def confined(root, relative):
    root = root.resolve()
    path = (root / relative).resolve()
    require(path.is_relative_to(root), 'source checker path escapes corpus')
    return path


def check_artifact(request):
    seconds = request.get('seconds', 30)
    require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0, 'invalid checker seconds')
    deadline = time.monotonic() + seconds
    files = Files(request.get('max_file_bytes', 256 * 1024 * 1024), deadline)
    corpus, source = Path(request['corpus']), Path(request['source'])
    manifest = json.loads(files.read(corpus / 'manifest.json', request.get('manifest_sha256')))
    acquisition = json.loads(files.read(source / 'acquisition.json', manifest['acquisition_sha256']))
    rows = [row for row in manifest['queries'] if row['name'] == request['query']]
    require(len(rows) == 1 and rows[0]['status'] == 'imported', 'unknown or unimported source query')
    query = rows[0]
    require(query['kind'] == 'EF', 'source replay supports only existential properties')
    sources = {entry['path']: entry for entry in acquisition['files']}
    contents = []
    for field in ('source_lola', 'source_formula'):
        name = query[field]
        require(query[field + '_sha256'] == sources[name]['sha256'], 'source identity differs from acquisition')
        contents.append(files.read(confined(source / 'upstream', name), query[field + '_sha256']).decode())
    mapping = json.loads(files.read(confined(corpus, query['source_mapping']), query['source_mapping_sha256']))
    answer = json.loads(files.read(Path(request['answer'])))
    if answer.get('kind') == 'original-property-v1':
        require(answer.get('property_id') == query['property_id'] and answer.get('property_kind') == 'EF', 'wrong original property identity')
        require(answer.get('verdict') == 'reachable' and answer.get('property_truth') is True and answer.get('deadline_exceeded') is False, 'not a timely positive property proposal')
        require(type(answer.get('branch_count')) is int and answer['branch_count'] == len(query['branches']), 'source property branch count mismatch')
        attempts = answer.get('attempts')
        require(type(attempts) is list, 'invalid property attempts')
        positive = [a for a in attempts if type(a) is dict and type(a.get('outcome')) is dict and a['outcome'].get('verdict') == 'reachable']
        require(len(positive) == 1, 'expected one positive branch')
        branch = positive[0].get('branch')
        outcome = positive[0]['outcome']
    else:
        branch, outcome = request.get('branch', 0), answer
    require(type(branch) is int and 0 <= branch < len(query['branches']), 'invalid positive branch')
    entry = query['branches'][branch]
    canonical = json.loads(files.read(confined(corpus, entry['path']), entry['sha256']))
    result = replay(*contents, mapping, canonical, outcome, deadline=deadline, max_work=request.get('max_work', 200_000_000))
    files.unchanged()
    result.pop('marking')
    return dict(result, query=query['name'], branch=branch, property_truth=True,
                translation_scope='net mapping and original source formula replay; no negative proof checking')

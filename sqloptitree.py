import sqlparse
import pydot
import random

PROJECTION = 'projection'
SELECTION = 'selection'
ENTITY = 'entity'
PRODUCT = 'product'
NATURAL_JOIN = 'natural_join'
# INNER_JOIN = 'inner_join'

VALID_KEYWORDS = ['SELECT', 'FROM', 'WHERE', 'JOIN']

MERGE = None

class SQLTreeNode(object):
    def __init__(self, category, value=None, _id=None):
        self.category = category
        self.value = value
        self.parent = None
        self.children = []
        self.id = _id

    def __str__(self):
        return self.to_string()

    def to_string(self, string='', tabs=''):
        string += tabs + SQLTreeNode.__get_label(self, 0) + '\n'
        tabs += '>'
        for child in self.children:
            string = child.to_string(string=string, tabs=tabs)

        return string
    
    def plot(self):
        g = pydot.Dot(graph_type='graph')
        name = ''.join([random.choice('0123456789abcdef') for i in range(10)])

        SQLTreeNode.__to_pydot(g, self.get_root())
        g.write_png('static/output/' + name + '.png')

        return name

    @staticmethod
    def __to_pydot(pydot_root, node, count=0):
        pydot_node = pydot.Node(SQLTreeNode.__get_label(node, count), shape=SQLTreeNode.__get_shape(node))
        count = count + 1
        pydot_root.add_node(pydot_node)

        for child in node.children:
            pydot_child = pydot.Node(SQLTreeNode.__get_label(child, count), shape=SQLTreeNode.__get_shape(child))
            edge = pydot.Edge(pydot_node, pydot_child)
            pydot_root.add_edge(edge)
            SQLTreeNode.__to_pydot(pydot_root, child, count)

    @staticmethod
    def __get_label(node, count):
        value = str(node.value) if node.value else ''

        if node.category == PROJECTION:
            return '\u03C0 ' + value
        elif node.category == SELECTION:
            return '\u03C3 ' + value
        elif node.category == PRODUCT:
            return '\u2A2F ' + str(count) + ' ' + value
        elif node.category == NATURAL_JOIN:
            return '\u2A1D ' + str(count) + ' ' + value
        else:
            return node.value.get_alias() if node.value.has_alias() else value

    def to_list(self, flatten=[]):
        flatten.append(self)
        for child in self.children:
            child.to_list(flatten)
        
        return flatten
        

    @staticmethod
    def __get_shape(node):
        if node.category == ENTITY:
            return 'circle'
        else:
            return 'none'

    def get_root(self):
        node = self
        while node.parent != None:
            node = node.parent

        return node

    def get_leafs(self, leafs=[]):
        if(self.is_leaf() and self not in leafs):
            leafs.append(self)
        else:
            for child in self.children:
                child.get_leafs(leafs)
        
        return leafs

    def is_root(self):
        return self.parent == None

    def is_leaf(self):
        return len(self.children) == 0
    
    def add_child(self, node):
        if node.parent != None:
            node.parent.remove_child(node)

        node.parent = self

        self.children.append(node)

    def add_children(self, nodes):
        for node in nodes:
            self.add_child(node)

    def add_before(self, node):
        self.parent.remove_child(self)
        node.parent.remove_child(node)

        self.parent.children.append(node)
        for child in node.children:
            child.parent = node.parent
            node.parent.children.append(child)

        node.children = [self]

        node.parent = self.parent
        self.parent = node

    def remove_child(self, node):
        self.children.remove(node)

    def has_child(self, child):
        if child in self.children:
            return True
        else:
            for my_child in self.children:
                if my_child.has_child(child):
                    return True
        
        return False

    def find(self, category):
        found = None
        for child in self.children:
            if child.category == category:
                found = child
            else:
                found = child.find(category)
        
        return found

    def find_closest_parent(self, node_a, node_b):
        parent = node_a.parent
        while not parent.has_child(node_b) and parent != None:
            parent = parent.parent

        return parent

    def get_entities(self):
        tokens = self.value.tokens
        entities = []
        for token in tokens:
            if isinstance(token, sqlparse.sql.Identifier):
                entities.append(token.tokens[0].normalized)

        return entities

    def merge(self, node):
        node.parent.remove_child(node)
        for child in node.children:
            child.parent = node.parent
            node.parent.children.append(child)

        if not isinstance(self.value, sqlparse.sql.TokenList):
            self.value = sqlparse.sql.TokenList([self.value, MERGE, node.value])
        else:
            tokens = self.value.tokens
            tokens.append(MERGE)
            tokens = tokens + node.value.tokens
            self.value = sqlparse.sql.TokenList(tokens)

    @staticmethod
    def from_query(query):
        root = SQLTreeNode(PROJECTION, query.tokens[2])
        where = SQLTreeNode(SELECTION, query.tokens[-1])

        tables = SQLTreeNode.__parse_products(query)

        root.add_child(where)
        where.add_child(tables)

        return root

    @staticmethod
    def __parse_products(query):
        # Token 4 is FROM Keyword
        from_table = query.token_next(4)
        # Case 1: Regular Product
        if isinstance(from_table[1], sqlparse.sql.IdentifierList):
            first = list(from_table[1].get_identifiers())[0]
            relation_a = SQLTreeNode(ENTITY, first, _id=first.get_alias())
            for identifier in list(from_table[1].get_identifiers())[1:]:
                relation_b = SQLTreeNode(ENTITY, identifier, _id=identifier.get_alias())
                product = SQLTreeNode(PRODUCT)
                product.add_children([relation_a, relation_b])

                relation_a = product
            
            return relation_a
        else:
            next_token = query.token_next(from_table[0])

            # Case 2: Join
            if next_token[1].is_keyword and next_token[1].normalized == 'JOIN':
                join_token = next_token

                value = query.token_next(join_token[0])[1]
                relation_a = SQLTreeNode(ENTITY, value, _id=value.get_alias())
                join_token = query.token_next(join_token[0] + 2)
                while join_token[1]:
                    value = query.token_next(join_token[0])[1]
                    relation_b = SQLTreeNode(ENTITY, value, _id=value.get_alias())
                    join = SQLTreeNode(NATURAL_JOIN)
                    join.add_children([relation_a, relation_b])

                    relation_a = join

                    join_token = query.token_next(join_token[0] + 2)
                
                return relation_a
            else:
                # Case 3: No product
                return SQLTreeNode(ENTITY, from_table[1])

class SQLQuery(object):
    def __init__(self, query):
        self.query = query
        self.parser = sqlparse.parse(query)
        # cleaning whitespaces tokens
        self.tokens = self._remove_whitespaces()
        self.tree = None

    def _remove_whitespaces(self):
        if not self.parser:
            return []
        return [token for token in self.parser[0].tokens if not token.is_whitespace]

    def is_valid(self):
        # Look for single statement
        if len(self.parser) != 1:
            return False
        # Validate scope keywords (SELECT, FROM, WHERE, JOIN)
        keywords = []
        from_info = None
        join_idx = []
        where_token = None
        for token in self.tokens:
            if token.is_keyword:
                if token.normalized not in VALID_KEYWORDS:
                    return False
                keywords.append(token)
                if token.normalized == 'FROM':
                    from_info = self.parser[0].token_next(self.parser[0].token_index(token))[1]
                elif token.normalized == 'JOIN':
                    join_idx.append(self.parser[0].token_index(token))
            elif isinstance(token, sqlparse.sql.Where):
                keywords.append(token)
                where_token = token

        # Look for SELECT/FROM(/WHERE) structure
        if len(keywords) < 2:
            return False
        elif keywords[0].normalized != 'SELECT' or keywords[1].normalized != 'FROM':
            return False
        elif where_token != None and not isinstance(keywords[-1], sqlparse.sql.Where):
            return False

        # Check for only JOIN or only Product
        product = isinstance(from_info, sqlparse.sql.IdentifierList)
        join = len(join_idx) > 0

        if product and join:
            return False

        # In case of JOIN or Product, check for alias
        alias_list = []
        identifier_filter = lambda token: isinstance(token, sqlparse.sql.Identifier) and len(token.tokens) > 1
        if product:
            if any(isinstance(token, sqlparse.sql.Identifier) and not token.has_alias() for token in from_info.tokens):
                return False
            
            alias_list = [token.get_alias() for token in filter(identifier_filter, from_info.tokens)]
        elif join:
            alias_list = [from_info.get_name()]
            for i in join_idx:
                token = self.parser[0].token_next(i)[1]
                if not token.has_alias():
                    return False
                else:
                    alias_list.append(token.get_alias())

        if isinstance(self.tokens[1], sqlparse.sql.IdentifierList):
            select_attrs = self.tokens[1].tokens
            select_identifiers = list(filter(identifier_filter, select_attrs))
        elif isinstance(self.tokens[1], sqlparse.sql.Identifier):
            select_identifiers = [self.tokens[1]]


        where_identifiers = []
        if where_token:
            where_identifiers = list(filter(identifier_filter, where_token.tokens))

        identifiers = select_identifiers + where_identifiers

        found_alias = list(map(lambda ident: ident.tokens[0].normalized, identifiers))
        
        if len(set(found_alias) - set(alias_list)):
            return False

        if any(alias not in alias_list for alias in found_alias):
            return False

        # WHERE clause check
        where_valid_keywords = ['AND', 'OR']
        if where_token:
            token = (0, where_token.token_first())
        else:
            token = (None, None)

        global MERGE
        while token[1]:
            token = where_token.token_next(token[0])
            if token[1]:
                if not isinstance(token[1], sqlparse.sql.Comparison) and not token[1].is_keyword:
                    return False
                elif token[1].is_keyword and token[1].normalized not in where_valid_keywords:
                    return False
                
                if not MERGE and token[1].is_keyword and token[1].normalized == 'AND':
                    MERGE = token[1]

        return True

    def optimize(self):
        stmt = self.tokens
        self.tree = SQLTreeNode.from_query(self.parser[0])
        steps = []
        self.do_optimization_steps(steps)

        return steps

    def do_optimization_steps(self, steps):
        steps.append((0, self.tree.plot()))
        self.step1()
        steps.append((1, self.tree.plot()))
        self.step2()
        steps.append((2, self.tree.plot()))
        self.step4()
        steps.append((4, self.tree.plot()))
        self.step5()
        steps.append((5, self.tree.plot()))

    # Break selection
    def step1(self):
        selection = self.tree.find(SELECTION)

        # Lookup for OR operation
        if any(token.is_keyword and token.normalized == 'OR' for token in selection.value.tokens):
            return

        pieces = filter(lambda t: isinstance(t, sqlparse.sql.Comparison), selection.value.tokens)
        nodes = list(map(lambda p: SQLTreeNode(SELECTION, p), pieces))

        for i in range(len(nodes) - 1):
            nodes[i].add_child(nodes[i+1])

        self.tree.add_child(nodes[0])
        nodes[-1].add_children(selection.children)
        self.tree.remove_child(selection)

    def step2(self):
        # Get tree as list
        nodes = self.tree.to_list()
        leafs = self.tree.get_leafs()

        # Get all selections
        selections = filter(lambda node: node.category == SELECTION, nodes)

        for selection in selections:
            # get all tables involved into that selection
            entities = selection.get_entities()
            
            # a.name = 'John' or a.col1 = a.col2
            if len(entities) == 1:
                entity = list(filter(lambda node: node.id == entities[0], leafs))[0]
            # a.name = b.name
            elif len(entities) > 1:
                entity = self.tree.find_closest_parent(entities[0], entities[1])

            if entity.parent.category == SELECTION:
                entity.parent.merge(selection)
            else:
                entity.add_before(selection)
        
        print(self.tree)
        
    
    def step4(self):
        pass
    
    def step5(self):
        pass
    
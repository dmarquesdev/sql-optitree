import sqlparse
import pydot

PROJECTION = 'projection'
SELECTION = 'selection'
ENTITY = 'entity'
PRODUCT = 'product'
PRODUCT_JOIN = 'product_join'

VALID_KEYWORDS = ['SELECT', 'FROM', 'WHERE', 'JOIN']

class SQLTreeNode(object):
    def __init__(self, category, value=None):
        self.category = category
        self.value = value
        self.parent = None
        self.children = []

    def plot(self, name):
        g = pydot.Dot(graph_type='graph')

        SQLTreeNode.__to_pydot(g, self.get_root())
        g.write_png('output/' + name + '.png')

    @staticmethod
    def __to_pydot(pydot_root, node):
        pydot_node = pydot.Node(SQLTreeNode.__get_label(node), shape=SQLTreeNode.__get_shape(node))
        pydot_root.add_node(pydot_node)

        for child in node.children:
            pydot_child = pydot.Node(SQLTreeNode.__get_label(child), shape=SQLTreeNode.__get_shape(child))
            edge = pydot.Edge(pydot_node, pydot_child)
            pydot_root.add_edge(edge)
            SQLTreeNode.__to_pydot(pydot_root, child)

    @staticmethod
    def __get_label(node):
        if node.category == PROJECTION:
            return '\u03C0 ' + str(node.value)
        elif node.category == SELECTION:
            return '\u03C3 ' + str(node.value)
        elif node.category == PRODUCT:
            return '\u2A2F ' + str(node.value)
        elif node.category == PRODUCT_JOIN:
            return '\u2A1D ' + str(node.value)
        else:
            return str(node.value)

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
    
    def add_child(self, node):
        if node.parent != None:
            node.parent.remove_child(node)

        node.parent = self

        self.children.append(node)

    def add_children(self, nodes):
        for node in nodes:
            self.add_child(node)

    def remove_child(self, node):
        self.children.remove(node)

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
            relation_a = SQLTreeNode(ENTITY, from_table[1].get_identifiers()[0])
            for identifier in from_table[1].get_identifiers()[1:]:
                relation_b = SQLTreeNode(ENTITY, identifier)
                product = SQLTreeNode(PRODUCT)
                product.add_children([relation_a, relation_b])

                relation_a = product
            
            return relation_a
        else:
            next_token = query.token_next(from_table[0])

            # Case 2: Join
            if next_token[1].is_keyword and next_token[1].normalized == 'JOIN':
                join_token = next_token

                relation_a = SQLTreeNode(ENTITY, query.token_next(join_token[0])[1])
                join_token = query.token_next(join_token[0] + 2)
                while join_token[1]:
                    relation_b = SQLTreeNode(ENTITY, query.token_next(join_token[0])[1])
                    join = SQLTreeNode(PRODUCT_JOIN)
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
        self.tree = None

    def is_valid(self):
        # Look for single statement
        if len(self.parser) != 1:
            return False
        # Validate scope keywords (SELECT, FROM, WHERE, JOIN)
        keywords = []
        from_info = None
        join_idx = []
        where_token = None
        for token in self.parser[0].tokens:
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

        if isinstance(self.parser[0].tokens[2], sqlparse.sql.IdentifierList):
            select_attrs = self.parser[0].tokens[2].tokens
            select_identifiers = list(filter(identifier_filter, select_attrs))
        elif isinstance(self.parser[0].tokens[2], sqlparse.sql.Identifier):
            select_identifiers = [self.parser[0].tokens[2]]


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

        while token[1]:
            token = where_token.token_next(token[0])
            if token[1]:
                if not isinstance(token[1], sqlparse.sql.Comparison) and not token[1].is_keyword:
                    return False
                elif token[1].is_keyword and token[1].normalized not in where_valid_keywords:
                    return False

        return True

    def optimize(self):
        stmt = self.parser[0].tokens
        self.tree = SQLTreeNode.from_query(self.parser[0])
        self.tree.plot('test')
        return stmt

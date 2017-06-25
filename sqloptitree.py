import sqlparse
import pydot

PROJECTION = 'projection'
SELECTION = 'selection'
ENTITY = 'entity'
PRODUCT = 'product'

VALID_KEYWORDS = ['SELECT', 'FROM', 'WHERE', 'ON', 'JOIN']


class SQLTreeNode(object):
    def __init__(self, category, value, parent=None, children=None):
        self.category = category
        self.value = value
        self.parent = parent
        self.children = children

    def plot(self):
        pass

    def add_node_before(self, node):
        pass

    def add_child(self, node):
        pass

    def remove_child(self, node):
        pass

    @staticmethod
    def from_query(query):
        return

class SQLQuery(object):
    def __init__(self, query):
        self.query = query
        self.parser = sqlparse.parse(query)
        self.tree = None

    def is_valid(self):
        # Look for single statement
        if len(self.parser) != 1:
            return False
        # Validate scope keywords (SELECT, FROM, WHERE, JOIN, ON)
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

        # TODO tratar ON dos joins

        identifiers = select_identifiers + where_identifiers

        found_alias = list(map(lambda ident: ident.tokens[0].normalized, identifiers))
        
        if len(set(found_alias) - set(alias_list)):
            return False

        if any(alias not in alias_list for alias in found_alias):
            return False

        # TODO tratar WHERE

        return True

    def optimize(self):
        stmt = self.parser[0].tokens
        #self.tree = SQLTreeNode.from_query(self.parser[0])
        return stmt

    '''
    WIP: Redo this using the SQLTreeNode
    '''

    def _to_tree(self, stmt):
        tree = {}
        for token in stmt.tokens:
            if isinstance(token, sqlparse.sql.IdentifierList):
                tree['select'] = [x for x in token.get_identifiers()]
            elif isinstance(token, sqlparse.sql.Where):
                tree['where'] = [x for x in token.tokens if (x.is_keyword
                                                             and
                                                             x.normalized !=
                                                             'WHERE')or isinstance(x,
                                                                                   sqlparse.sql.Comparison)
                                 ]
            elif token.is_keyword and token.normalized == 'FROM':
                tree['from'] = stmt.token_next(stmt.token_index(token))[1]

        return tree

    '''
    WIP: Redo this using the SQLTreeNode
    '''

    def _plot_graph(self, tree):
        g = pydot.Dot(graph_type='graph')
        projection = ', '.join(map(lambda x: x.get_name(), tree['select']))
        selection = ' '.join(map(lambda x: x.value, tree['where']))

        pNode = pydot.Node(projection, shape='none')
        sNode = pydot.Node(selection, shape='none')

        g.add_node(pNode)
        g.add_node(sNode)

        edge = pydot.Edge(pNode, sNode)
        g.add_edge(edge)

        for table in tree['from']:
            edge = pydot.Edge(selection, table.value)
            g.add_edge(edge)

        g.write_png('output/test.png')
        return tree

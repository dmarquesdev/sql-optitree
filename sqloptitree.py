import sqlparse
import pydot

PROJECTION = 'projection'
SELECTION = 'selection'
ENTITY = 'entity'
PRODUCT = 'product'

VALID_KEYWORDS = ['SELECT', 'FROM', 'WHERE', 'ON', 'JOIN']

class SQLTreeNode(object):

    def __init__(self, category, value, parent=None, children=[]):
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
        for token in self.parser[0].tokens:
            if token.is_keyword:
                keywords.append(token)
                if token.normalized not in VALID_KEYWORDS:
                    return False
        
        # Look for SELECT/FROM(/WHERE) structure
        # In case of JOIN and Product, check for alias
        return True

    def optimize(self):
        stmt = self.parser[0].tokens
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

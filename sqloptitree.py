import sqlparse
import pydot

class SQLQuery(object):
    def __init__(self, query):
        self.query = query
        self.parser = sqlparse.parse(query)
        self.tree = {}

    def is_valid(self):
        return True

    def optimize(self):
        stmt = self.parser[0]
        self.tree = self._to_tree(stmt)
        return self._plot_graph(self.tree)

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

        g.write_png('tmp/test.png')
        return tree

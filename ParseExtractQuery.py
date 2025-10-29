from antlr4 import *
from grammer.SQLiteLexer import SQLiteLexer
from grammer.SQLiteParser import SQLiteParser

class ParseNormalizeQuery():
    
    def __init__(self):
        self.query = ""
        self.literals_list = []

    def replace_literals_and_inner_selects(self , sql : str):
        input_stream = InputStream(sql)
        lexer = SQLiteLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = SQLiteParser(token_stream)
        tree = parser.sql_stmt_list()
        flag = True  # This flag tracks if we're inside the first (outermost) SELECT

        def replace_node_with_placeholder(ctx):
            start = ctx.start.tokenIndex
            stop = ctx.stop.tokenIndex
            # here we replace all tokens with empty string and then replace initial with ? 
            for i in range(start, stop + 1):
                token_stream.tokens[i].text = ""
            token_stream.tokens[start].text = "?"

        def traverse(node):
            nonlocal flag

            if hasattr(node, "getRuleIndex"):
                rule = parser.ruleNames[node.getRuleIndex()]
                if rule == "literal_value":
                    self.literals_list.append(node.getText())
                    replace_node_with_placeholder(node)
                    return
                if rule == "any_name":
                    text = node.getText()
                    # Detect if it's double-quoted — treat as literal, not alias
                    if text.startswith('"') and text.endswith('"'):
                        self.literals_list.append(text)
                        replace_node_with_placeholder(node)
                        return

                # Replace only inner SELECTs
                if rule == "select_core":
                    if flag:  # First select_core = outermost
                        flag = False  # Next ones will be considered inner
                    else:
                        replace_node_with_placeholder(node)
                        return

            # Recursively process children
            for i in range(node.getChildCount()):
                traverse(node.getChild(i))

        traverse(tree)
        final_sql = " ".join(t.text for t in token_stream.tokens if t.text.strip() != "" and t.type != parser.EOF)
        return final_sql


    def get_sql_text_from_context(self, ctx, token_stream: CommonTokenStream):
        """
        Returns the exact SQL text for a parser rule context,
        rebuilt from tokens with clean spacing.
        """
        start = ctx.start.tokenIndex
        stop = ctx.stop.tokenIndex
        tokens = token_stream.tokens[start:stop + 1]
        sql_text = " ".join(t.text for t in tokens if t.text.strip() != "")
        return sql_text

    def extract_select_blocks(self , node, parser, token_stream, results, depth=0):
        if hasattr(node, "getRuleIndex"):
            rule = parser.ruleNames[node.getRuleIndex()]

            if rule == "select_core":
                sql_text = self.get_sql_text_from_context(node, token_stream)
                results.append(sql_text)

        for i in range(node.getChildCount()):
            child = node.getChild(i)
            self.extract_select_blocks(child, parser, token_stream, results, depth + 1)

    def parse_and_extract(self,sql_query):
        input_stream = InputStream(sql_query)
        lexer = SQLiteLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = SQLiteParser(token_stream)
        tree = parser.sql_stmt_list()


        results = []
        self.extract_select_blocks(tree, parser, token_stream, results)

        return results



    

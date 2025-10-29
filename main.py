from ParseExtractQuery import ParseNormalizeQuery
import re , hashlib , json , copy

class QueryPlanManager():
    def __init__(self):

        self.query_cache = {}
        self.cache_metrics = {
                "requests": 0,
                "hits": 0,
                "misses": 0,
                }
        self.parser_and_normalizer = ParseNormalizeQuery()

    def generate_dummy_plan(self , query: str):
        """
        Generate a dummy JSON query plan for cache miss.
        """

        # Generate unique plan ID using hash of query
        plan_id = "PLN_" + hashlib.md5(query.encode()).hexdigest()[:8]

        # Decide plan type based on query keywords
        plan_type = "Index Scan" if re.search(r"\bWHERE\b", query, re.IGNORECASE) else "Full Table Scan"

        # Extract table names (basic heuristic)
        tables = re.findall(r"FROM\s+(\w+)", query, re.IGNORECASE)
        joins = re.findall(r"JOIN\s+(\w+)", query, re.IGNORECASE)
        all_tables = list(set(tables + joins))

        plan = {
            "plan_id": plan_id,
            "plan_type": plan_type,
            "tables": all_tables or ["unknown_table"]
        }
        return json.dumps(plan, indent=4)

    def fetch_or_generate_query_plan(self , sql_query) -> dict:
        parsed_and_splitted_queries = self.parser_and_normalizer.parse_and_extract(sql_query=sql_query)

        normalized_queries = []
        for sub_query in parsed_and_splitted_queries :
            normalized_form = self.parser_and_normalizer.replace_literals_and_inner_selects(sub_query)
            # Below logic is written to convert IN (? , ? , ... , ?) into ( ? ) as parser normalization logic replaces each literal with ?
            normalized_form = re.sub(
                            r"\bIN\s*\(\s*(?:\?\s*,\s*)+\?\s*\)",
                            "IN ( ? )",
                            normalized_form,
                            flags=re.IGNORECASE,
                        )
            normalized_queries.append(normalized_form)
        # At this stage we have normalized form of input query along with its nested sub-queries
        # Now we check for plan present in cache or not
        execution_plan = {}
        for normalized_query in normalized_queries :
            self.cache_metrics["requests"] += 1
            if normalized_query in self.query_cache :
                self.cache_metrics["hits"] += 1
                # Here plan found in cache
                execution_plan[normalized_form] = self.query_cache[normalized_query]
            else :
                self.cache_metrics["misses"] += 1
                # Here plan not found in cache, so we have to generate it
                new_plan = self.generate_dummy_plan(normalized_query)
                self.query_cache[normalized_query] = new_plan
                execution_plan[normalized_query] = new_plan
        # print("*")
        # print(self.parser_and_normalizer.literals_list)
        literals = copy.deepcopy(self.parser_and_normalizer.literals_list)
        self.parser_and_normalizer.literals_list.clear()
        return execution_plan , literals
    
    
query1 = """SELECT name FROM users
WHERE dept_id IN (
    SELECT id FROM department
    WHERE manager_id IN (
        SELECT id FROM managers WHERE salary > 50000
    )
);"""
query2 = """SELECT name FROM users
WHERE dept_id IN (
    SELECT id FROM department
    WHERE manager_id IN (
        SELECT id FROM managers WHERE salary > 70000
    )
);"""

query_plan_manager = QueryPlanManager()

plan1 , literals1 = query_plan_manager.fetch_or_generate_query_plan(query1)
print("Query " , query1 , " is executing with below plan ")
print(plan1)
print("Associated Literals : " , literals1)
print("="*100)  

plan2 , literals2 = query_plan_manager.fetch_or_generate_query_plan(query2)
print("="*100)
print("Query " , query2 , " is executing with below plan ")
print(plan2)
print("Associated Literals : " , literals2)
print("="*100)

# print(query_plan_manager.query_cache)
print(query_plan_manager.cache_metrics)



from ParseExtractQuery import ParseNormalizeQuery
import re, hashlib, json, copy


class QueryPlanManager():
    def __init__(self):
        self.query_cache = {}
        self.cache_metrics = {
            "requests": 0,
            "hits": 0,
            "misses": 0,
        }
        self.parser_and_normalizer = ParseNormalizeQuery()
        self.flag = True
        self.total_complexity_score = 0

    def estimate_query_complexity(self , query: str) -> int:
    
        query = query.lower()
        score = 0
        score += query.count("where") * 3
        score += query.count("and") * 2
        score += query.count("or") * 2
        score += query.count("join") * 5
        score += query.count("group by") * 4
        score += query.count("order by") * 4
        score += query.count("having") * 3
        if re.search(r"\b(sum|count|min|max|avg)\b", query):
            score += 5
        score += query.count("select") 
        return max(score , 1)

    def generate_dummy_plan(self, query: str):
        """
        Generate a dummy JSON query plan for cache miss.
        """
        plan_id = "PLN_" + hashlib.md5(query.encode()).hexdigest()[:8]
        plan_type = "Index Scan" if re.search(r"\bWHERE\b", query, re.IGNORECASE) else "Full Table Scan"

        tables = re.findall(r"FROM\s+(\w+)", query, re.IGNORECASE)
        joins = re.findall(r"JOIN\s+(\w+)", query, re.IGNORECASE)
        all_tables = list(set(tables + joins))

        plan = {
            "plan_id": plan_id,
            "plan_type": plan_type,
            "tables": all_tables or ["unknown_table"],
        }
        return json.dumps(plan, indent=4)

    def fetch_or_generate_query_plan(self, sql_query) -> dict:
        parsed_and_splitted_queries = self.parser_and_normalizer.parse_and_extract(sql_query)

        normalized_queries = []
        for sub_query in parsed_and_splitted_queries:
            normalized_form = self.parser_and_normalizer.replace_literals_and_inner_selects(sub_query)

            normalized_form = re.sub(
                r"\bIN\s*\(\s*(?:\?\s*,\s*)+\?\s*\)",
                "IN ( ? )",
                normalized_form,
                flags=re.IGNORECASE,
            )

            normalized_queries.append(normalized_form)

        execution_plan = {}
        for normalized_query in normalized_queries:
            self.cache_metrics["requests"] += 1

            if normalized_query in self.query_cache and self.flag:
                self.cache_metrics["hits"] += 1
                execution_plan[normalized_query] = self.query_cache[normalized_query]
            else:
                self.cache_metrics["misses"] += 1
                new_plan = self.generate_dummy_plan(normalized_query)
                self.query_cache[normalized_query] = new_plan
                execution_plan[normalized_query] = new_plan
                self.total_complexity_score += self.estimate_query_complexity(normalized_query)

        literals = copy.deepcopy(self.parser_and_normalizer.literals_list)
        self.parser_and_normalizer.literals_list.clear()

        return execution_plan, literals


if __name__ == "__main__" : 
    # ---------------- Test Driver ---------------- #
    query1 = """SELECT name FROM users
    WHERE dept_id IN (1,2,3)"""

    query2 = """SELECT name FROM users
    WHERE dept_id IN (SELECT ids FROM admin WHERE pf > 30000) """

    query_plan_manager = QueryPlanManager()
    plan1, literals1 = query_plan_manager.fetch_or_generate_query_plan(query1)
    print("Query:", query1, "\nexecuting with plan:")
    print(plan1)
    print("Associated Literals:", literals1)
    print("=" * 100)

    plan2, literals2 = query_plan_manager.fetch_or_generate_query_plan(query2)
    print("Query:", query2, "\nexecuting with plan:")
    print(plan2)
    print("Associated Literals:", literals2)
    print("=" * 100)

    print("Cache Metrics:", query_plan_manager.cache_metrics)

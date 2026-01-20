# firestorm/agents/analyst-agent.py
"""
Data Analyst Agent - Runs complex analytical queries
Complex JOINs, aggregations, cohort analysis, patient with slow queries
"""

import random
import time
import json
import logging
from agents.base_agent import BaseAgent
from agents.personas import PERSONAS

logger = logging.getLogger(__name__)

class AnalystAgent(BaseAgent):
    """Data analyst agent implementation - complex analytical queries"""
    
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(agent_id, "analyst", **kwargs)
        self.persona = PERSONAS["analyst"]
        
    def run_session(self, duration_minutes: int = None):
        """Run an analyst session"""
        if duration_minutes is None:
            duration_minutes = random.randint(*self.persona["session_duration_minutes"])
        
        session_start = time.time()
        session_end = session_start + (duration_minutes * 60)
        
        self.start_session()
        
        action_count = 0
        while time.time() < session_end:
            # Ask Ollama what to do next
            action = self._decide_next_action(action_count)
            
            if action:
                self._execute_action(action)
                action_count += 1
            
            # Long think time - analysts are patient
            think_time = random.uniform(*self.persona["think_time_seconds"])
            time.sleep(min(think_time, 60))  # Cap at 60 seconds for testing
        
        self.end_session()
    
    def _decide_next_action(self, action_count: int) -> dict:
        """Use Ollama to decide next action"""
        
        recent_actions = self.session_memory[-3:] if self.session_memory else []
        context = f"Queries run: {len(self.session_memory)}\nRecent: {recent_actions}"
        
        prompt = f"""You are a data analyst running complex analytical queries.

{context}

What analysis should you run next? Consider:
- You've completed {action_count} queries
- You run complex JOINs (3-4 tables)
- You do large aggregations (GROUP BY, COUNT, SUM, AVG)
- You're patient with slow queries
- You iterate and refine queries
- You focus on business insights

Respond with JSON only:
{{"action": "revenue_analysis", "params": {{"period": "7days", "group_by": "category"}}}}

Available actions: revenue_analysis, customer_segments, product_performance, 
                   cohort_analysis, trend_analysis, export_data
"""
        
        response = self._call_ollama(prompt, self.persona["system_prompt"])
        
        try:
            action = json.loads(response)
            self.session_memory.append(action)
            return action
        except:
            return self._fallback_action()
    
    def _fallback_action(self) -> dict:
        """Random fallback based on Heavy-Reader query breakdown percentages"""
        breakdown = self.persona.get("query_breakdown", {})
        actions = list(breakdown.keys())
        weights = list(breakdown.values())
        
        if not actions:
            actions = ["large_simple_query", "large_join_simple", "aggregate_query"]
            weights = [0.35, 0.35, 0.3]
        
        action_name = random.choices(actions, weights=weights)[0]
        
        if action_name == "large_simple_query":
            use_order = random.random() < 0.5
            use_group = random.random() < 0.5
            
            bundle = random.choice(["products", "orders", "users"])
            # Bundle-specific GROUP BY fields
            if bundle == "products":
                group_by_field = "category" if use_group else None
            elif bundle == "orders":
                group_by_field = "status" if use_group else None
            else:  # users
                group_by_field = None  # users has no good grouping field
            
            return {
                "action": action_name,
                "params": {
                    "bundle": bundle,
                    "limit": random.randint(1000, 2000),
                    "order_by": random.choice(["DocumentID", "created_at"]) if use_order else None,
                    "group_by": group_by_field
                }
            }
        elif action_name == "large_join_simple":
            use_group = random.random() < 0.5
            return {
                "action": action_name,
                "params": {
                    "bundles": ["products", "reviews"],
                    "limit": random.randint(500, 1000),
                    "group_by": "category" if use_group else None
                }
            }
        elif action_name == "large_join_complex":
            use_order = random.random() < 0.5
            use_group = random.random() < 0.5
            return {
                "action": action_name,
                "params": {
                    "bundles": ["orders", "order_items", "products"],
                    "limit": random.randint(200, 500),
                    "order_by": "total" if use_order else None,
                    "group_by": "category" if use_group else None
                }
            }
        elif action_name == "aggregate_query":
            return {
                "action": action_name,
                "params": {
                    "bundle": random.choice(["orders", "products", "reviews"]),
                    "aggregates": ["COUNT", "SUM", "AVG"]
                }
            }
        else:  # bulk_simple_query
            return {
                "action": "bulk_simple_query",
                "params": {
                    "bundle": random.choice(["products", "orders"]),
                    "limit": random.randint(1000, 2000)
                }
            }
    
    def _execute_action(self, action: dict):
        """Execute the analytical query"""
        action_name = action.get("action")
        params = action.get("params", {})
        
        query = self._build_query(action_name, params)
        
        if query:
            result = self._execute_query(query)
            logger.info(f"[{self.agent_id}] {action_name}: {result.get('success')} ({result.get('latency_ms', 0):.2f}ms)")
    
    def _build_query(self, action_name: str, params: dict) -> str:
        """Build SyndrQL query - Heavy-Reader breakdown (large-scale reads)"""
        
        # New action types for Heavy-Reader
        if action_name == "large_simple_query":
            bundle = params.get("bundle", "products")
            limit = params.get("limit", random.randint(1000, 2000))
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            query = f'SELECT "DocumentID", "name", "price" FROM "{bundle}"'
            
            if order_by:
                query += f' ORDER BY "{order_by}" DESC'
            if group_by:
                query += f' GROUP BY "{group_by}"'
            
            query += f' LIMIT {limit};'
            return query
        
        elif action_name == "large_join_simple":
            bundles = params.get("bundles", ["products", "reviews"])
            limit = params.get("limit", random.randint(500, 1000))
            group_by = params.get("group_by")
            
            # Always ORDER BY, sometimes GROUP BY
            query = f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", AVG("{bundles[1]}"."rating") as "avg_rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"
                      WHERE ("{bundles[1]}"."rating" >= 3)'''
            
            if group_by:
                query += f' GROUP BY "{bundles[0]}"."category"'
            
            query += f' ORDER BY "avg_rating" DESC LIMIT {limit};'
            return query
        
        elif action_name == "large_join_complex":
            bundles = params.get("bundles", ["orders", "order_items", "products"])
            limit = params.get("limit", random.randint(200, 500))
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            query = f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[2]}"."name", SUM("{bundles[1]}"."quantity") as "total_qty"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."order_id"
                      JOIN "{bundles[2]}" ON "{bundles[1]}"."product_id" == "{bundles[2]}"."DocumentID"
                      WHERE (("{bundles[0]}"."status" == "completed") AND ("{bundles[2]}"."price" > 50))'''
            
            if group_by:
                query += f' GROUP BY "{bundles[2]}"."category"'
            
            if order_by:
                query += f' ORDER BY "total_qty" DESC'
            
            query += f' LIMIT {limit};'
            return query
        
        elif action_name == "aggregate_query":
            bundle = params.get("bundle", "orders")
            
            return f'''SELECT "category",
                             COUNT(*) as "count",
                             SUM("total") as "sum_total",
                             AVG("total") as "avg_total"
                      FROM "{bundle}"
                      GROUP BY "category"
                      LIMIT 1000;'''
        
        elif action_name == "bulk_simple_query":
            bundle = params.get("bundle", "products")
            limit = params.get("limit", random.randint(1000, 2000))
            
            # No ORDER BY, no GROUP BY
            return f'''SELECT "DocumentID", "name", "price"
                      FROM "{bundle}"
                      LIMIT {limit};'''
        
        # Legacy actions
        if action_name == "revenue_analysis":
            group_by = params.get("group_by", "category")
            
            if group_by == "category":
                # Join orders -> order_items -> products, group by category
                return f'''SELECT "products"."category", 
                                 COUNT("orders"."DocumentID") as "order_count",
                                 SUM("order_items"."quantity") as "units_sold",
                                 SUM("order_items"."price") as "summed_price",
                                 AVG("order_items"."price") as "avg_price"
                          FROM "orders"
                          JOIN "order_items" ON "orders"."DocumentID" == "order_items"."order_id"
                          JOIN "products" ON "order_items"."product_id" == "products"."DocumentID"
                          WHERE ("orders"."status" == "completed")
                          GROUP BY "products"."category"
                          ORDER BY "summed_price" DESC;'''
            else:
                return f'''SELECT COUNT(*) as "total_orders", SUM("total") as "total_revenue"
                          FROM "orders" 
                          WHERE ("status" == "completed");'''
        
        elif action_name == "customer_segments":
            metric = params.get("metric", "total_spent")
            
            # Customer segmentation by spending
            return f'''SELECT "users"."DocumentID", "users"."email",
                             COUNT("orders"."DocumentID") as "order_count",
                             SUM("orders"."total") as "total_spent",
                             AVG("orders"."total") as "avg_order_value"
                      FROM "users"
                      JOIN "orders" ON "users"."DocumentID" == "orders"."user_id"
                      WHERE ("orders"."status" == "completed")
                      GROUP BY "users"."DocumentID", "users"."email"
                      ORDER BY "total_spent" DESC
                      LIMIT 100;'''
        
        elif action_name == "product_performance":
            # Product performance with reviews and sales
            return f'''SELECT "products"."DocumentID", "products"."name", "products"."category",
                             COUNT("order_items"."order_id") as "times_ordered",
                             SUM("order_items"."quantity") as "units_sold",
                             AVG("reviews"."rating") as "avg_rating",
                             COUNT("reviews"."DocumentID") as "review_count"
                      FROM "products"
                      LEFT JOIN "order_items" ON "products"."DocumentID" == "order_items"."product_id"
                      LEFT JOIN "reviews" ON "products"."DocumentID" == "reviews"."product_id"
                      GROUP BY "products"."DocumentID", "products"."name", "products"."category"
                      ORDER BY "units_sold" DESC
                      LIMIT 50;'''
        
        elif action_name == "cohort_analysis":
            # Simplified cohort - orders by user registration
            return f'''SELECT "users"."created_at" as "cohort",
                             COUNT("users"."DocumentID") as "user_count",
                             COUNT("orders"."DocumentID") as "order_count",
                             SUM("orders"."total") as "revenue"
                      FROM "users"
                      LEFT JOIN "orders" ON "users"."DocumentID" == "orders"."user_id"
                      GROUP BY "users"."created_at"
                      ORDER BY "cohort" DESC
                      LIMIT 30;'''
        
        elif action_name == "trend_analysis":
            metric = params.get("metric", "orders")
            
            if metric == "orders":
                return f'''SELECT "created_at" as "date",
                                 COUNT(*) as "order_count",
                                 SUM("total") as "daily_revenue",
                                 AVG("total") as "avg_order_value"
                          FROM "orders"
                          WHERE ("status" == "completed")
                          GROUP BY "created_at"
                          ORDER BY "created_at" DESC
                          LIMIT 90;'''
            else:
                return f'''SELECT "category", COUNT(*) as "count" 
                          FROM "products" 
                          GROUP BY "category";'''
        
        elif action_name == "export_data":
            # Large data export query
            return f'''SELECT "orders"."DocumentID", "orders"."user_id", "orders"."total", "orders"."status", "orders"."created_at",
                             "order_items"."product_id", "order_items"."quantity", "order_items"."price",
                             "products"."name", "products"."category"
                      FROM "orders"
                      JOIN "order_items" ON "orders"."DocumentID" == "order_items"."order_id"
                      JOIN "products" ON "order_items"."product_id" == "products"."DocumentID"
                      LIMIT 1000;'''
        
        return None

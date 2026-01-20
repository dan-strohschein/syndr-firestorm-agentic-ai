# firestorm/agents/admin-agent.py
"""
Admin Agent - Store administrator managing inventory and orders
Performs bulk operations, generates reports, manages users
"""

import random
import time
import json
import logging
from agents.base_agent import BaseAgent
from agents.personas import PERSONAS

logger = logging.getLogger(__name__)

class AdminAgent(BaseAgent):
    """Admin agent implementation - bulk operations and management"""
    
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(agent_id, "admin", **kwargs)
        self.persona = PERSONAS["admin"]
        
    def run_session(self, duration_minutes: int = None):
        """Run an admin session"""
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
            
            # Longer think time - admins work in bursts
            think_time = random.uniform(*self.persona["think_time_seconds"])
            time.sleep(min(think_time, 30))  # Cap at 30 seconds for testing
        
        self.end_session()
    
    def _decide_next_action(self, action_count: int) -> dict:
        """Use Ollama to decide next action"""
        
        recent_actions = self.session_memory[-5:] if self.session_memory else []
        context = f"Actions so far: {len(self.session_memory)}\nRecent: {recent_actions}"
        
        prompt = f"""You are a store administrator managing the platform.

{context}

What administrative task should you do next? Consider:
- You've completed {action_count} tasks
- You do bulk operations (50-200 items)
- You process orders and update statuses
- You generate reports for insights
- You verify changes after updates
- You manage inventory levels

Respond with JSON only:
{{"action": "bulk_update_inventory", "params": {{"category": "Electronics", "stock_adjust": 50}}}}

Available actions: bulk_update_inventory, process_orders, generate_report, 
                   view_pending_orders, update_product, moderate_reviews
"""
        
        response = self._call_ollama(prompt, self.persona["system_prompt"])
        
        try:
            action = json.loads(response)
            self.session_memory.append(action)
            return action
        except:
            return self._fallback_action()
    
    def _fallback_action(self) -> dict:
        """Random fallback based on Heavy-Writer query breakdown percentages"""
        breakdown = self.persona.get("query_breakdown", {})
        actions = list(breakdown.keys())
        weights = list(breakdown.values())
        
        if not actions:
            actions = ["bulk_create", "bulk_update", "simple_query"]
            weights = [0.35, 0.35, 0.3]
        
        action_name = random.choices(actions, weights=weights)[0]
        
        if action_name == "bulk_create":
            return {
                "action": action_name,
                "params": {
                    "bundle": random.choice(["products", "users"]),
                    "count": random.randint(100, 200)
                }
            }
        elif action_name == "bulk_update":
            return {
                "action": action_name,
                "params": {
                    "bundle": "products",
                    "category": random.choice(["Electronics", "Clothing", "Home"]),
                    "count": random.randint(100, 200)
                }
            }
        elif action_name == "bulk_delete":
            return {
                "action": action_name,
                "params": {
                    "bundle": "reviews",
                    "count": random.randint(50, 100)
                }
            }
        elif action_name == "simple_query":
            return {
                "action": action_name,
                "params": {
                    "bundle": random.choice(["products", "orders", "users"])
                }
            }
        elif action_name == "join_simple":
            return {
                "action": action_name,
                "params": {
                    "bundles": ["products", "reviews"]
                }
            }
        else:  # join_complex
            return {
                "action": "join_complex",
                "params": {
                    "bundles": ["orders", "order_items", "products"]
                }
            }
    
    def _execute_action(self, action: dict):
        """Execute the admin action"""
        action_name = action.get("action")
        params = action.get("params", {})
        
        query = self._build_query(action_name, params)
        
        if query:
            result = self._execute_query(query)
            logger.info(f"[{self.agent_id}] {action_name}: {result.get('success')} ({result.get('latency_ms', 0):.2f}ms)")
    
    def _build_query(self, action_name: str, params: dict) -> str:
        """Build SyndrQL query - Heavy-Writer breakdown (bulk operations)"""
        
        # New action types for Heavy-Writer
        if action_name == "bulk_create":
            bundle = params.get("bundle", "products")
            count = params.get("count", random.randint(100, 200))
            
            # Simulate bulk create (would normally loop, but showing intent)
            if bundle == "products":
                return f'''ADD DOCUMENT TO BUNDLE "products"
                          WITH (
                              {{\"name\" = "Bulk Product {random.randint(10000,99999)}"}},
                              {{\"price\" = {random.uniform(10, 500):.2f}}},
                              {{\"category\" = "{random.choice(["Electronics", "Clothing", "Home"])}"}},
                              {{\"stock\" = {random.randint(100, 1000)}}}
                          );
                          -- NOTE: This represents 1 of {count} bulk inserts'''
            else:
                return f'''ADD DOCUMENT TO BUNDLE "users"
                          WITH (
                              {{\"name\" = "Bulk User {random.randint(10000,99999)}"}},
                              {{\"email\" = "bulkuser{random.randint(10000,99999)}@example.com"}}
                          );
                          -- NOTE: This represents 1 of {count} bulk inserts'''
        
        elif action_name == "bulk_update":
            bundle = params.get("bundle", "products")
            category = params.get("category", "Electronics")
            count = params.get("count", random.randint(100, 200))
            
            return f'''UPDATE DOCUMENTS IN BUNDLE "{bundle}"
                      ("stock" = 100)
                      WHERE ("category" == "{category}");
                      -- NOTE: Bulk update targeting {count} documents'''
        
        elif action_name == "bulk_delete":
            bundle = params.get("bundle", "reviews")
            count = params.get("count", random.randint(50, 100))
            
            return f'''DELETE DOCUMENTS FROM "{bundle}"
                      WHERE ("rating" <= 2);
                      -- NOTE: Bulk delete targeting {count} documents'''
        
        elif action_name == "simple_query":
            bundle = params.get("bundle", "products")
            # Bundle-specific field selections
            if bundle == "products":
                return f'''SELECT "DocumentID", "name", "stock"
                          FROM "{bundle}"
                          LIMIT 100;'''
            elif bundle == "orders":
                return f'''SELECT "DocumentID", "total", "status"
                          FROM "{bundle}"
                          LIMIT 100;'''
            else:  # users
                return f'''SELECT "DocumentID", "name", "email"
                          FROM "{bundle}"
                          LIMIT 100;'''
        
        elif action_name == "join_simple":
            bundles = params.get("bundles", ["products", "reviews"])
            return f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", COUNT("{bundles[1]}"."DocumentID") as "review_count"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"
                      WHERE ("{bundles[0]}"."stock" < 50)
                      GROUP BY "{bundles[0]}"."DocumentID"
                      LIMIT 100;'''
        
        elif action_name == "join_complex":
            bundles = params.get("bundles", ["orders", "order_items", "products"])
            return f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[2]}"."category", COUNT(*) as "total_orders"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."order_id"
                      JOIN "{bundles[2]}" ON "{bundles[1]}"."product_id" == "{bundles[2]}"."DocumentID"
                      WHERE (("{bundles[0]}"."status" == "completed") AND ("{bundles[2]}"."price" > 100))
                      GROUP BY "{bundles[2]}"."category"
                      LIMIT 100;'''
        
        # Legacy actions
        if action_name == "bulk_update_inventory":
            category = params.get("category", "Electronics")
            stock_adjust = params.get("stock_adjust", 50)
            
            # Simulated bulk update - get products first, then update
            return f'''SELECT "DocumentID", "name", "stock" 
                      FROM "products" 
                      WHERE ("category" == "{category}")
                      LIMIT 100;'''
        
        elif action_name == "process_orders":
            status = params.get("status", "pending")
            limit = params.get("limit", 50)
            
            return f'''SELECT "DocumentID", "user_id", "total", "status", "created_at" 
                      FROM "orders" 
                      WHERE ("status" == "{status}")
                      ORDER BY "created_at" ASC
                      LIMIT {limit};'''
        
        elif action_name == "generate_report":
            report_type = params.get("report_type", "sales")
            days = params.get("days", 7)
            
            if report_type == "sales":
                return f'''SELECT COUNT(*) as "order_count", SUM("total") as "total_revenue"
                          FROM "orders" 
                          WHERE ("status" == "completed");'''
            elif report_type == "inventory":
                return f'''SELECT "category", COUNT(*) as "product_count", SUM("stock") as "total_stock"
                          FROM "products" 
                          GROUP BY "category";'''
            else:
                return f'''SELECT COUNT(*) FROM "products";'''
        
        elif action_name == "view_pending_orders":
            return f'''SELECT "DocumentID", "user_id", "total", "created_at" 
                      FROM "orders" 
                      WHERE ("status" == "pending")
                      ORDER BY "created_at" ASC
                      LIMIT 100;'''
        
        elif action_name == "update_product":
            product_id = params.get("product_id", random.randint(1, 5000))
            
            # Get product first (simulated update)
            return f'''SELECT "DocumentID", "name", "price", "stock" 
                      FROM "products" 
                      WHERE ("DocumentID" == {product_id});'''
        
        elif action_name == "moderate_reviews":
            min_rating = params.get("min_rating", 1)
            
            return f'''SELECT "DocumentID", "user_id", "product_id", "rating", "comment" 
                      FROM "reviews" 
                      WHERE ("rating" <= {min_rating})
                      ORDER BY "created_at" DESC
                      LIMIT 50;'''
        
        return None

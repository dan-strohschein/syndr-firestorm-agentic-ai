# firestorm/agents/power-user-agent.py
"""
Power User Agent - Frequent shopper who knows what they want
Efficient, uses filters, completes purchases, writes reviews
"""

import random
import time
import json
import logging
from agents.base_agent import BaseAgent
from agents.personas import PERSONAS

logger = logging.getLogger(__name__)

class PowerUserAgent(BaseAgent):
    """Power user agent implementation - efficient and experienced"""
    
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(agent_id, "power_user", **kwargs)
        self.persona = PERSONAS["power_user"]
        self.user_id = hash(agent_id) % 10000  # Consistent user ID
        
    def run_session(self, duration_minutes: int = None):
        """Run a power user session"""
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
            
            # Short think time - power users are fast
            think_time = random.uniform(*self.persona["think_time_seconds"])
            time.sleep(think_time)
        
        self.end_session()
    
    def _decide_next_action(self, action_count: int) -> dict:
        """Use Ollama to decide next action"""
        
        recent_actions = self.session_memory[-5:] if self.session_memory else []
        context = f"Actions so far: {len(self.session_memory)}\nRecent: {recent_actions}"
        
        prompt = f"""You are a power user shopping efficiently online.

{context}

What do you want to do next? Consider:
- You've taken {action_count} actions
- You're experienced - use filters, compare products
- You complete purchases quickly
- You check order history and write reviews
- You use wishlists

Respond with JSON only:
{{"action": "quick_purchase", "params": {{"product_id": 123}}}}

Available actions: browse_products, search_products, quick_purchase, check_reviews, 
                   view_order_history, write_review, manage_wishlist, track_order
"""
        
        response = self._call_ollama(prompt, self.persona["system_prompt"])
        
        try:
            action = json.loads(response)
            self.session_memory.append(action)
            return action
        except:
            return self._fallback_action()
    
    def _fallback_action(self) -> dict:
        """Random fallback based on Normal-Writer query breakdown percentages"""
        breakdown = self.persona.get("query_breakdown", {})
        actions = list(breakdown.keys())
        weights = list(breakdown.values())
        
        if not actions:
            actions = ["create_document", "update_documents", "simple_query"]
            weights = [0.35, 0.35, 0.3]
        
        action_name = random.choices(actions, weights=weights)[0]
        
        if action_name == "create_document":
            return {
                "action": action_name,
                "params": {
                    "bundle": random.choice(["products", "orders", "users"]),
                    "count": random.randint(1, 10)
                }
            }
        elif action_name == "update_documents":
            return {
                "action": action_name,
                "params": {
                    "bundle": "products",
                    "where": f'(\"category\" == \"{random.choice(["Electronics", "Clothing"])}\")'
                }
            }
        elif action_name == "delete_documents":
            return {
                "action": action_name,
                "params": {
                    "bundle": random.choice(["reviews", "cart_items"]),
                    "where": '(\"id\" > 0)'
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
        """Execute the action"""
        action_name = action.get("action")
        params = action.get("params", {})
        
        query = self._build_query(action_name, params)
        
        if query:
            result = self._execute_query(query)
            logger.info(f"[{self.agent_id}] {action_name}: {result.get('success')} ({result.get('latency_ms', 0):.2f}ms)")
    
    def _build_query(self, action_name: str, params: dict) -> str:
        """Build SyndrQL query - Normal-Writer breakdown"""
        
        # New action types for Normal-Writer
        if action_name == "create_document":
            bundle = params.get("bundle", "products")
            count = params.get("count", random.randint(1, 10))
            
            if bundle == "products":
                return f'''ADD DOCUMENT TO BUNDLE "products"
                          WITH (
                              {{\"name\" = "Product {random.randint(1000,9999)}"}},
                              {{\"price\" = {random.uniform(10, 500):.2f}}},
                              {{\"category\" = "{random.choice(["Electronics", "Clothing", "Home"])}"}},
                              {{\"stock\" = {random.randint(10, 100)}}}
                          );'''
            elif bundle == "orders":
                return f'''ADD DOCUMENT TO BUNDLE "orders"
                          WITH (
                              {{\"user_id\" = {random.randint(1, 10000)}}},
                              {{\"total\" = {random.uniform(50, 500):.2f}}},
                              {{\"status\" = "pending"}}
                          );'''
            else:
                return f'''ADD DOCUMENT TO BUNDLE "users"
                          WITH (
                              {{\"name\" = "User {random.randint(1000,9999)}"}},
                              {{\"email\" = "user{random.randint(1000,9999)}@example.com"}}
                          );'''
        
        elif action_name == "update_documents":
            bundle = params.get("bundle", "products")
            where = params.get("where", '(\"id\" > 0)')
            count = random.randint(1, 10)
            
            return f'''UPDATE DOCUMENTS IN BUNDLE "{bundle}"
                      ("stock" = 100)
                      WHERE {where};'''
        
        elif action_name == "delete_documents":
            bundle = params.get("bundle", "reviews")
            where = params.get("where", '(\"rating\" <= 2)')
            count = random.randint(1, 5)
            
            return f'''DELETE DOCUMENTS FROM "{bundle}"
                      WHERE {where};'''
        
        elif action_name == "simple_query":
            bundle = params.get("bundle", "products")
            return f'''SELECT "DocumentID", "name", "price"
                      FROM "{bundle}"
                      LIMIT 50;'''
        
        elif action_name == "join_simple":
            bundles = params.get("bundles", ["products", "reviews"])
            return f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", "{bundles[1]}"."rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"
                      WHERE ("{bundles[1]}"."rating" >= 4)
                      LIMIT 50;'''
        
        elif action_name == "join_complex":
            bundles = params.get("bundles", ["orders", "order_items", "products"])
            return f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[2]}"."name", "{bundles[1]}"."quantity"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."order_id"
                      JOIN "{bundles[2]}" ON "{bundles[1]}"."product_id" == "{bundles[2]}"."DocumentID"
                      WHERE (("{bundles[0]}"."status" == "completed") AND ("{bundles[2]}"."price" > 100))
                      LIMIT 50;'''
        
        # Legacy actions (keep for backward compatibility)
        if action_name == "browse_products":
            category = params.get("category", "")
            filters = params.get("filters", {})
            limit = params.get("limit", 20)
            
            where_clauses = []
            if category:
                where_clauses.append(f'("category" == "{category}")')
            if "price_max" in filters:
                where_clauses.append(f'("price" <= {filters["price_max"]})')
            if "min_rating" in filters:
                where_clauses.append(f'("rating" >= {filters["min_rating"]})')
            
            where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            return f'''SELECT "DocumentID", "name", "price", "category", "rating", "stock" 
                      FROM "products" 
                      {where}
                      ORDER BY "rating" DESC, "price" ASC
                      LIMIT {limit};'''
        
        elif action_name == "search_products":
            keywords = params.get("keywords", "laptop")
            return f'''SELECT "DocumentID", "name", "price", "rating", "stock" 
                      FROM "products" 
                      WHERE ("name" LIKE "%{keywords}%")
                      ORDER BY "rating" DESC
                      LIMIT 15;'''
        
        elif action_name == "quick_purchase":
            product_id = params.get("product_id", random.randint(1, 5000))
            quantity = params.get("quantity", 1)
            
            # Create order
            return f'''ADD DOCUMENT TO BUNDLE "orders" 
                      WITH (
                          {{"user_id" = {self.user_id}}},
                          {{"total" = 100.0}},
                          {{"status" = "completed"}},
                          {{"created_at" = "{time.strftime('%Y-%m-%d %H:%M:%S')}"}}
                      );'''
        
        elif action_name == "check_reviews":
            product_id = params.get("product_id", random.randint(1, 5000))
            return f'''SELECT "rating", "comment", "created_at" 
                      FROM "reviews" 
                      WHERE ("product_id" == {product_id})
                      ORDER BY "created_at" DESC
                      LIMIT 10;'''
        
        elif action_name == "view_order_history":
            return f'''SELECT "DocumentID", "total", "status", "created_at" 
                      FROM "orders" 
                      WHERE ("user_id" == {self.user_id})
                      ORDER BY "created_at" DESC
                      LIMIT 20;'''
        
        elif action_name == "write_review":
            product_id = params.get("product_id", random.randint(1, 5000))
            rating = params.get("rating", random.randint(3, 5))
            comment = params.get("comment", "Great product!")
            
            return f'''ADD DOCUMENT TO BUNDLE "reviews" 
                      WITH (
                          {{"user_id" = {self.user_id}}},
                          {{"product_id" = {product_id}}},
                          {{"rating" = {rating}}},
                          {{"comment" = "{comment}"}},
                          {{"created_at" = "{time.strftime('%Y-%m-%d %H:%M:%S')}"}}
                      );'''
        
        elif action_name == "track_order":
            order_id = params.get("order_id", random.randint(1, 5000))
            return f'''SELECT "DocumentID", "status", "created_at", "total" 
                      FROM "orders" 
                      WHERE ("DocumentID" == {order_id});'''
        
        return None

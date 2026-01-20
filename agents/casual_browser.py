# firestorm/agents/casual_browser.py
import random
import time
import logging
from agents.base_agent import BaseAgent
from agents.personas import PERSONAS

logger = logging.getLogger(__name__)

class CasualBrowserAgent(BaseAgent):
    """Casual browser agent implementation"""
    
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(agent_id, "casual_browser", **kwargs)
        self.persona = PERSONAS["casual_browser"]
        
    def run_session(self, duration_minutes: int = None):
        """Run a browsing session"""
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
            
            # Think time (realistic pause)
            think_time = random.uniform(*self.persona["think_time_seconds"])
            time.sleep(think_time)
        
        self.end_session()
    
    def _decide_next_action(self, action_count:  int) -> dict:
        """Use Ollama to decide next action"""
        
        # Build context prompt
        recent_actions = self.session_memory[-5:] if self.session_memory else []
        context = f"Actions so far: {len(self.session_memory)}\nRecent:  {recent_actions}"
        
        prompt = f"""You are in an online shopping session. 

{context}

What do you want to do next?  Consider:
- You've taken {action_count} actions so far
- Be realistic - browse, search, maybe add to cart
- You might get distracted or abandon the session
- You're a casual browser, not a buyer

Respond with JSON only: 
{{"action": "browse_products", "params": {{"category": "Electronics", "sort_by": "rating", "limit": 20}}}}

Or choose from:  browse_products, search_products, view_product, add_to_cart, view_cart, remove_from_cart
"""
        
        response = self._call_ollama(prompt, self.persona["system_prompt"])
        
        try:
            # Parse JSON response
            import json
            action = json.loads(response)
            self.session_memory.append(action)
            return action
        except: 
            # Fallback to random action if LLM fails
            return self._fallback_action()
    
    def _fallback_action(self) -> dict:
        """Random fallback based on query breakdown percentages"""
        # Use weighted random selection based on persona query_breakdown
        breakdown = self.persona.get("query_breakdown", {})
        actions = list(breakdown.keys())
        weights = list(breakdown.values())
        
        if not actions:
            # Default fallback if no breakdown defined
            actions = ["simple_query", "join_simple", "create_document"]
            weights = [0.4, 0.3, 0.3]
        
        action_name = random.choices(actions, weights=weights)[0]
        
        # Generate params based on action type
        if action_name == "simple_query":
            use_order = random.random() < 0.5
            use_group = random.random() < 0.5 and not use_order
            
            bundle = random.choice(["products", "orders", "users"])
            # Bundle-specific fields
            if bundle == "products":
                fields = ["DocumentID", "name"]
                order_by = "name" if use_order else None
                group_by = "category" if use_group else None
            elif bundle == "orders":
                fields = ["DocumentID", "total"]
                order_by = "total" if use_order else None
                group_by = "status" if use_group else None
            else:  # users
                fields = ["DocumentID", "name"]
                order_by = "name" if use_order else None
                group_by = None  # users has no good grouping field
            
            return {
                "action": action_name,
                "params": {
                    "bundle": bundle,
                    "fields": fields,
                    "order_by": order_by,
                    "group_by": group_by
                }
            }
        elif action_name == "join_simple":
            return {
                "action": action_name,
                "params": {
                    "bundles": ["products", "reviews"],
                    "where": f'("products"."rating" >= 4)'
                }
            }
        elif action_name == "join_complex":
            use_order = random.random() < 0.5
            use_group = random.random() < 0.5
            return {
                "action": action_name,
                "params": {
                    "bundles": ["products", "reviews", "users"],
                    "where": f'(("products"."rating" >= 4) AND ("reviews"."rating" >= 3))',
                    "order_by": "products.rating" if use_order else None,
                    "group_by": "products.category" if use_group else None
                }
            }
        elif action_name == "create_document":
            return {
                "action": action_name,
                "params": {
                    "bundle": random.choice(["products", "users", "reviews"]),
                    "count": random.randint(1, 5)
                }
            }
        elif action_name == "update_documents":
            return {
                "action": action_name,
                "params": {
                    "bundle": "products",
                    "where": f'("category" == "{random.choice(["Electronics", "Clothing"])}")',
                    "count": random.randint(1, 5)
                }
            }
        elif action_name == "delete_documents":
            return {
                "action": action_name,
                "params": {
                    "bundle": "reviews",
                    "where": f'("rating" <= 2)',
                    "count": random.randint(1, 3)
                }
            }
        
        return {"action": "simple_query", "params": {"bundle": "products"}}
    
    def _execute_action(self, action: dict):
        """Convert action to SyndrQL query and execute"""
        action_name = action.get("action")
        params = action.get("params", {})
        
        query = self._build_query(action_name, params)
        
        if query:
            result = self._execute_query(query)
            logger.info(f"[{self.agent_id}] {action_name}: {result. get('success')} ({result.get('latency_ms', 0):.2f}ms)")
    
    def _build_query(self, action_name: str, params: dict) -> str:
        """Build SyndrQL query based on action - Normal-Reader breakdown"""
        
        # New action types based on Normal-Reader persona
        if action_name == "simple_query":
            bundle = params.get("bundle", "products")
            fields = params.get("fields", ["DocumentID", "name"])
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            fields_str = ", ".join([f'"{f}"' for f in fields])
            query = f'SELECT {fields_str} FROM "{bundle}"'
            
            if order_by:
                query += f' ORDER BY "{order_by}" DESC'
            if group_by:
                query += f' GROUP BY "{group_by}"'
            
            query += " LIMIT 50;"
            return query
        
        elif action_name == "join_simple":
            bundles = params.get("bundles", ["products", "reviews"])
            where = params.get("where", '')
            
            return f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", "{bundles[1]}"."rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"
                      WHERE {where}
                      LIMIT 50;'''
        
        elif action_name == "join_complex":
            bundles = params.get("bundles", ["products", "reviews"])
            where = params.get("where", '')
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            query = f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"'''
            
            if len(bundles) > 2:
                query += f' JOIN "{bundles[2]}" ON "{bundles[1]}"."user_id" == "{bundles[2]}"."DocumentID"'
            
            query += f' WHERE {where}'
            
            if order_by:
                query += f' ORDER BY "{order_by}" DESC'
            if group_by:
                query += f' GROUP BY "{group_by}"'
            
            query += " LIMIT 50;"
            return query
        
        elif action_name == "create_document":
            bundle = params.get("bundle", "products")
            
            if bundle == "products":
                return f'''ADD DOCUMENT TO BUNDLE "products"
                          WITH (
                              {{\"name\" = "New Product {random.randint(1000,9999)}"}},
                              {{\"price\" = {random.uniform(10, 500):.2f}}},
                              {{\"category\" = "{random.choice(["Electronics", "Clothing", "Home"])}"}},
                              {{\"stock\" = {random.randint(10, 100)}}}
                          );'''
            elif bundle == "users":
                return f'''ADD DOCUMENT TO BUNDLE "users"
                          WITH (
                              {{\"name\" = "User {random.randint(1000,9999)}"}},
                              {{\"email\" = "user{random.randint(1000,9999)}@example.com"}}
                          );'''
            else:
                return f'''ADD DOCUMENT TO BUNDLE "{bundle}"
                          WITH ({{\"id\" = {random.randint(1,1000)}}});'''
        
        elif action_name == "update_documents":
            bundle = params.get("bundle", "products")
            where = params.get("where", '(\"id\" > 0)')
            
            return f'''UPDATE DOCUMENTS IN BUNDLE "{bundle}"
                      ("stock" = 100)
                      WHERE {where};'''
        
        elif action_name == "delete_documents":
            bundle = params.get("bundle", "reviews")
            where = params.get("where", '(\"rating\" <= 2)')
            
            return f'''DELETE DOCUMENTS FROM "{bundle}"
                      WHERE {where};'''
        
        # Legacy actions (keep for backward compatibility)
        if action_name == "browse_products":
            category = params.get("category", "")
            sort_by = params.get("sort_by", "rating")
            limit = params.get("limit", 20)
            
            where = f'WHERE ("category" == "{category}")' if category else ""
            order_map = {
                "price":  'ORDER BY "price" ASC',
                "rating": 'ORDER BY "rating" DESC',
                "newest": 'ORDER BY "created_at" DESC'
            }
            order = order_map.get(sort_by, 'ORDER BY "rating" DESC')
            
            return f'''SELECT "DocumentID", "name", "price", "category", "rating", "stock" 
                      FROM "products" 
                      {where}
                      {order}
                      LIMIT {limit};'''
        
        elif action_name == "search_products": 
            keywords = params.get("keywords", "")
            return f'''SELECT "DocumentID", "name", "price", "rating" 
                      FROM "products" 
                      WHERE ("name" == "{keywords}")
                      LIMIT 10;'''
        
        elif action_name == "add_to_cart":
            product_id = params.get("product_id", random.randint(1, 5000))
            quantity = params.get("quantity", 1)
            user_id = hash(self.agent_id) % 10000  # Simulate user ID
            
            return f'''ADD DOCUMENT TO BUNDLE "cart_items" 
                      WITH (
                          {{"user_id" = {user_id}}},
                          {{"product_id" = {product_id}}},
                          {{"quantity" = {quantity}}}
                      );'''
        
        elif action_name == "view_cart":
            user_id = hash(self.agent_id) % 10000
            return f'''SELECT "cart_items"."product_id", "products"."name", "products"."price", "cart_items"."quantity"
                      FROM "cart_items"
                      JOIN "products" ON "cart_items"."product_id" == "products"."DocumentID"
                      WHERE ("cart_items"."user_id" == {user_id});'''
        
        return None
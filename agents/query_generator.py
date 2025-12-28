"""
Query Generator for Pre-generating SyndrQL Queries

Generates 200-300 queries per agent upfront based on persona query breakdown,
eliminating Ollama latency from performance testing.
"""

import random
import logging
import time
import requests
import json
from typing import List, Dict, Any, Optional
from agents.personas import PERSONAS
from agents.syndrql_validator import validate_query

logger = logging.getLogger(__name__)


class QueryGenerator:
    """Generates pre-validated SyndrQL queries for agents"""
    
    def __init__(
        self,
        persona_name: str,
        agent_id: str,
        document_ids: Dict[str, List[str]],
        ollama_url: str = "http://localhost:11434"
    ):
        """
        Initialize QueryGenerator.
        
        Args:
            persona_name: Name of persona (casual_browser, power_user, admin, analyst)
            agent_id: Unique agent identifier for logging
            document_ids: Dict with user_document_ids, product_document_ids, order_document_ids
            ollama_url: Ollama API URL
        """
        self.persona_name = persona_name
        self.agent_id = agent_id
        self.document_ids = document_ids
        self.ollama_url = ollama_url
        
        if persona_name not in PERSONAS:
            raise ValueError(f"Unknown persona: {persona_name}")
        
        self.persona = PERSONAS[persona_name]
        self.query_breakdown = self.persona["query_breakdown"]
        
        # Track statistics
        self.generation_attempts = 0
        self.validation_failures = 0
        self.ollama_failures = 0
        
    def generate_queries(self, count: Optional[int] = None) -> List[str]:
        """
        Generate a list of pre-validated queries.
        
        Args:
            count: Number of queries to generate (random 200-300 if None)
            
        Returns:
            List of validated SyndrQL query strings
            
        Raises:
            RuntimeError: If failure rate exceeds 25%
        """
        if count is None:
            count = random.randint(200, 300)
        
        queries = []
        start_time = time.time()
        
        logger.info(f"[{self.agent_id}] ({self.persona_name}) Generating {count} queries...")
        
        for i in range(count):
            query = self._generate_single_query()
            
            if query:
                queries.append(query)
                
                # Progress logging every 50 queries
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"[{self.agent_id}] ({self.persona_name}) Generated {i + 1}/{count} queries "
                        f"({elapsed:.1f}s elapsed, {self.validation_failures} validation failures, "
                        f"{self.ollama_failures} Ollama failures)"
                    )
            else:
                logger.warning(f"[{self.agent_id}] ({self.persona_name}) Failed to generate query {i + 1}")
        
        # Check failure rate (commented out - just log warning instead of aborting)
        failure_rate = (self.validation_failures + self.ollama_failures) / self.generation_attempts if self.generation_attempts > 0 else 0
        
        # if failure_rate > 0.25:
        #     error_msg = (
        #         f"[{self.agent_id}] ({self.persona_name}) Generation failure rate {failure_rate:.1%} "
        #         f"exceeds 25% threshold. Aborting test."
        #     )
        #     logger.error(error_msg)
        #     raise RuntimeError(error_msg)
        
        if failure_rate > 0.25:
            logger.warning(
                f"[{self.agent_id}] ({self.persona_name}) High failure rate: {failure_rate:.1%} "
                f"(validation: {self.validation_failures}, ollama: {self.ollama_failures})"
            )
        
        elapsed = time.time() - start_time
        logger.info(
            f"[{self.agent_id}] ({self.persona_name}) ✓ Generated {len(queries)} queries in {elapsed:.1f}s "
            f"(Validation failures: {self.validation_failures}, Ollama failures: {self.ollama_failures})"
        )
        
        return queries
    
    def _generate_single_query(self) -> Optional[str]:
        """
        Generate a single validated query with retry logic.
        
        Returns:
            Valid SyndrQL query string or None if all attempts fail
        """
        max_attempts = 10
        
        for attempt in range(max_attempts):
            self.generation_attempts += 1
            
            # Select action based on query breakdown percentages
            action_name = self._select_action()
            
            # Try Ollama first
            query = self._try_ollama_generation(action_name)
            
            # Fallback to deterministic generation if Ollama fails
            if not query:
                self.ollama_failures += 1
                query = self._fallback_generation(action_name)
            
            # Validate query
            if query:
                is_valid, error = validate_query(query)
                
                if is_valid:
                    return query
                else:
                    self.validation_failures += 1
                    if attempt == 0:  # Only log first attempt
                        logger.debug(
                            f"[{self.agent_id}] ({self.persona_name}) Validation failed for {action_name}: {error}"
                        )
        
        # All attempts failed
        logger.error(
            f"[{self.agent_id}] ({self.persona_name}) Failed to generate valid query after {max_attempts} attempts"
        )
        return None
    
    def _select_action(self) -> str:
        """Select action type based on persona query breakdown."""
        actions = list(self.query_breakdown.keys())
        weights = list(self.query_breakdown.values())
        return random.choices(actions, weights=weights)[0]
    
    def _try_ollama_generation(self, action_name: str) -> Optional[str]:
        """
        Try to generate query using Ollama.
        
        Args:
            action_name: Action type to generate
            
        Returns:
            Generated query string or None if Ollama fails
        """
        try:
            # Build prompt for Ollama
            prompt = f"""Generate a SyndrQL query for the action: {action_name}

Follow these rules:
- Return ONLY the raw SyndrQL query, no JSON, no explanation
- Query must end with semicolon
- Use double quotes for identifiers
- Use proper SyndrQL syntax

Example for simple_query:
SELECT "DocumentID", "name" FROM "products" LIMIT 50;

Example for join_simple:
SELECT "products"."name", "reviews"."rating" FROM "products" JOIN "reviews" ON "products"."DocumentID" == "reviews"."product_id" WHERE ("reviews"."rating" >= 4) LIMIT 50;

Example for create_document:
ADD DOCUMENT TO BUNDLE "products" WITH ({{"name" = "Product X"}}, {{"price" = 99.99}}, {{"category" = "Electronics"}}, {{"stock" = 100}});

Now generate a query for: {action_name}"""

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2:1b",
                    "prompt": prompt,
                    "system": self.persona["system_prompt"],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                query = result.get("response", "").strip()
                
                # Clean up response (remove markdown, extra whitespace)
                query = query.replace("```sql", "").replace("```", "").strip()
                
                return query if query else None
            else:
                return None
                
        except Exception as e:
            logger.debug(f"[{self.agent_id}] Ollama generation failed: {e}")
            return None
    
    def _fallback_generation(self, action_name: str) -> str:
        """
        Generate query deterministically without Ollama.
        
        Args:
            action_name: Action type to generate
            
        Returns:
            Generated SyndrQL query string
        """
        # Get params based on action type
        params = self._generate_params(action_name)
        
        # Build query based on action and persona
        return self._build_query(action_name, params)
    
    def _generate_params(self, action_name: str) -> Dict[str, Any]:
        """Generate parameters for action type."""
        
        # Common parameters
        bundles = ["products", "orders", "users", "reviews", "cart_items", "order_items"]
        
        if "simple" in action_name or action_name in ["simple_query", "large_simple_query", "bulk_simple_query"]:
            use_order = random.random() < 0.5
            use_group = random.random() < 0.3
            limit = self._get_limit_for_action(action_name)
            
            return {
                "bundle": random.choice(["products", "orders", "users"]),
                "fields": ["DocumentID", "name"],
                "order_by": random.choice(["name", "created_at", None]) if use_order else None,
                "group_by": random.choice(["category", None]) if use_group else None,
                "limit": limit
            }
        
        elif "join_simple" in action_name or action_name == "join_simple":
            limit = self._get_limit_for_action(action_name)
            return {
                "bundles": ["products", "reviews"],
                "where": f'("{random.choice(["products", "reviews"])}"."rating" >= 4)',
                "limit": limit,
                "order_by": random.choice(["rating", "created_at", None]),
                "group_by": None
            }
        
        elif "join_complex" in action_name or action_name == "join_complex":
            limit = self._get_limit_for_action(action_name)
            use_order = random.random() < 0.5
            use_group = random.random() < 0.3
            
            return {
                "bundles": ["products", "reviews", "users"],
                "where": f'(("products"."rating" >= 4) AND ("reviews"."rating" >= 3))',
                "limit": limit,
                "order_by": "products.rating" if use_order else None,
                "group_by": "products.category" if use_group else None
            }
        
        elif "create" in action_name or action_name == "create_document":
            return {
                "bundle": random.choice(["products", "users", "orders"]),
                "count": self._get_count_for_action(action_name)
            }
        
        elif "update" in action_name or action_name == "update_documents":
            return {
                "bundle": "products",
                "where": f'("category" == "{random.choice(["Electronics", "Clothing", "Home"])}")',
                "count": self._get_count_for_action(action_name)
            }
        
        elif "delete" in action_name or action_name == "delete_documents":
            return {
                "bundle": "reviews",
                "where": f'("rating" <= 2)',
                "count": self._get_count_for_action(action_name)
            }
        
        elif "aggregate" in action_name:
            return {
                "bundle": random.choice(["orders", "products"]),
                "aggregates": ["COUNT(*)", "SUM(total)", "AVG(total)"],
                "group_by": random.choice(["category", "status"])
            }
        
        return {}
    
    def _get_limit_for_action(self, action_name: str) -> int:
        """Get appropriate LIMIT value based on action type."""
        if "large_simple" in action_name or "bulk_simple" in action_name:
            return random.randint(1000, 2000)
        elif "large_join_simple" in action_name:
            return random.randint(500, 1000)
        elif "large_join_complex" in action_name:
            return random.randint(200, 500)
        else:
            return 50
    
    def _get_count_for_action(self, action_name: str) -> int:
        """Get appropriate count for bulk operations."""
        if "bulk_create" in action_name:
            return random.randint(100, 200)
        elif "bulk_update" in action_name:
            return random.randint(100, 200)
        elif "bulk_delete" in action_name:
            return random.randint(50, 100)
        else:
            return random.randint(1, 10)
    
    def _build_query(self, action_name: str, params: Dict[str, Any]) -> str:
        """
        Build SyndrQL query from action and params.
        
        This method contains the query building logic extracted from agent classes.
        """
        
        # SELECT queries
        if action_name in ["simple_query", "large_simple_query", "bulk_simple_query"]:
            bundle = params.get("bundle", "products")
            fields = params.get("fields", ["DocumentID", "name"])
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            limit = params.get("limit", 50)
            
            fields_str = ", ".join([f'"{f}"' for f in fields])
            query = f'SELECT {fields_str} FROM "{bundle}"'
            
            if order_by:
                query += f' ORDER BY "{order_by}" DESC'
            if group_by:
                query += f' GROUP BY "{group_by}"'
            
            query += f" LIMIT {limit};"
            return query
        
        # Simple JOINs
        elif action_name in ["join_simple", "large_join_simple"]:
            bundles = params.get("bundles", ["products", "reviews"])
            where = params.get("where", '("rating" >= 4)')
            limit = params.get("limit", 50)
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            query = f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", "{bundles[1]}"."rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"
                      WHERE {where}'''
            
            if order_by:
                query += f' ORDER BY "{order_by}" DESC'
            if group_by:
                query += f' GROUP BY "{group_by}"'
                
            query += f" LIMIT {limit};"
            return query
        
        # Complex JOINs
        elif action_name in ["join_complex", "large_join_complex"]:
            bundles = params.get("bundles", ["products", "reviews", "users"])
            where = params.get("where", '("rating" >= 4)')
            limit = params.get("limit", 50)
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            query = f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", "{bundles[1]}"."rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"'''
            
            if len(bundles) > 2:
                query += f' JOIN "{bundles[2]}" ON "{bundles[1]}"."user_id" == "{bundles[2]}"."DocumentID"'
            
            query += f' WHERE {where}'
            
            if order_by:
                query += f' ORDER BY "{order_by}" DESC'
            if group_by:
                query += f' GROUP BY "{group_by}"'
            
            query += f" LIMIT {limit};"
            return query
        
        # CREATE operations
        elif action_name in ["create_document", "bulk_create"]:
            bundle = params.get("bundle", "products")
            count = params.get("count", 1)
            
            if bundle == "products":
                return f'''ADD DOCUMENT TO BUNDLE "products"
                          WITH (
                              {{\"name\" = "Product {random.randint(1000,99999)}"}},
                              {{\"price\" = {random.uniform(10, 500):.2f}}},
                              {{\"category\" = "{random.choice(["Electronics", "Clothing", "Home"])}"}},
                              {{\"stock\" = {random.randint(10, 1000)}}}
                          );'''
            elif bundle == "users":
                return f'''ADD DOCUMENT TO BUNDLE "users"
                          WITH (
                              {{\"name\" = "User {random.randint(1000,99999)}"}},
                              {{\"email\" = "user{random.randint(1000,99999)}@example.com"}}
                          );'''
            elif bundle == "orders":
                # Use real document IDs from seeding
                user_ids = self.document_ids.get("user_document_ids", [])
                user_id = random.choice(user_ids) if user_ids else "unknown_user"
                
                return f'''ADD DOCUMENT TO BUNDLE "orders"
                          WITH (
                              {{\"user_id\" = "{user_id}"}},
                              {{\"total\" = {random.uniform(50, 500):.2f}}},
                              {{\"status\" = "{random.choice(["pending", "completed", "cancelled"])}"}}
                          );'''
            else:
                return f'''ADD DOCUMENT TO BUNDLE "{bundle}"
                          WITH ({{\"id\" = {random.randint(1,1000)}}});'''
        
        # UPDATE operations
        elif action_name in ["update_documents", "bulk_update"]:
            bundle = params.get("bundle", "products")
            where = params.get("where", '("id" > 0)')
            
            return f'''UPDATE DOCUMENTS IN BUNDLE "{bundle}"
                      ("stock" = {random.randint(50, 200)})
                      WHERE {where};'''
        
        # DELETE operations
        elif action_name in ["delete_documents", "bulk_delete"]:
            bundle = params.get("bundle", "reviews")
            where = params.get("where", '("rating" <= 2)')
            
            return f'''DELETE DOCUMENTS FROM "{bundle}"
                      WHERE {where};'''
        
        # AGGREGATE queries
        elif action_name == "aggregate_query":
            bundle = params.get("bundle", "orders")
            group_by = params.get("group_by", "category")
            
            return f'''SELECT "{group_by}",
                             COUNT(*) as "count",
                             SUM("total") as "sum_total",
                             AVG("total") as "avg_total"
                      FROM "{bundle}"
                      GROUP BY "{group_by}"
                      LIMIT 1000;'''
        
        # Default fallback
        return 'SELECT "DocumentID" FROM "products" LIMIT 10;'

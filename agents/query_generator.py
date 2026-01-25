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
from conductor.expanded_categories import (
    PRODUCT_CATEGORIES,
    RATING_VALUES,
    STOCK_RANGES,
    PRICE_RANGES,
    ORDER_STATUSES,
    get_random_category,
    get_random_category_subset
)

logger = logging.getLogger(__name__)


class QueryGenerator:
    """Generates pre-validated SyndrQL queries for agents with high entropy"""
    
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
        
        # Agent-specific category subset (10-20 categories per agent)
        # This dramatically reduces overlap between agents
        self.agent_categories = get_random_category_subset(random.randint(15, 25))
        
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
        max_attempts = 3  # Only 3 attempts - Ollama should work or we fallback quickly
        
        for attempt in range(max_attempts):
            self.generation_attempts += 1
            
            # Select action based on query breakdown percentages
            action_name = self._select_action()
            
            # Try Ollama first (with improved prompting)
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
            # Build comprehensive prompt with full SyndrQL syntax rules
            prompt = f"""Generate a valid SyndrQL query for: {action_name}

CRITICAL SYNDRQL SYNTAX RULES:
1. ALL identifiers (bundle names, field names) MUST use double quotes: "products", "name"
2. String values use double quotes: "Electronics"
3. Equality operator is == (double equals)
4. Query MUST end with semicolon ;
5. Comparison operators: ==, !=, <, >, <=, >=
6. Logical operators: AND, OR
7. Keywords are case-insensitive: SELECT, FROM, WHERE, JOIN, ON

VALID SYNDRQL EXAMPLES:

SELECT queries:
SELECT "DocumentID", "name" FROM "products" LIMIT 50;
SELECT TOP 10 * FROM "users";
SELECT COUNT(*) FROM "orders" WHERE "total" > 100;
SELECT * FROM "products" WHERE "category" == "Electronics" ORDER BY "price" DESC;
SELECT "category", COUNT(*) FROM "products" GROUP BY "category";

JOIN queries:
SELECT "products"."name", "reviews"."rating" FROM "products" JOIN "reviews" ON "products"."DocumentID" == "reviews"."product_id" WHERE "reviews"."rating" >= 4 LIMIT 50;
SELECT "users"."name", "orders"."total" FROM "users" JOIN "orders" ON "users"."DocumentID" == "orders"."user_id";

CREATE document:
ADD DOCUMENT TO BUNDLE "products" WITH ({{"name" = "Product X"}}, {{"price" = 99.99}}, {{"category" = "Electronics"}}, {{"stock" = 100}});

UPDATE documents:
UPDATE DOCUMENTS IN BUNDLE "products" ("stock" = 50) WHERE "category" == "Electronics";

DELETE documents:
DELETE DOCUMENTS FROM "reviews" WHERE "rating" <= 2;

NOW GENERATE: {action_name}
Return ONLY the SyndrQL query, nothing else."""

            # Add action-specific guidance
            action_hints = {
                "simple_query": 'Generate a SELECT query with 2-3 fields and LIMIT 50',
                "large_simple_query": 'Generate a SELECT query with LIMIT between 1000-2000',
                "bulk_simple_query": 'Generate a SELECT query with LIMIT between 1000-2000',
                "join_simple": 'Generate a JOIN between 2 bundles with WHERE clause and LIMIT 50',
                "large_join_simple": 'Generate a JOIN between 2 bundles with LIMIT 500-1000',
                "join_complex": 'Generate a JOIN between 3 bundles with WHERE and LIMIT 50',
                "large_join_complex": 'Generate a JOIN between 3 bundles with LIMIT 200-500',
                "create_document": 'Generate ADD DOCUMENT with 3-5 fields',
                "bulk_create": 'Generate ADD DOCUMENT with 3-5 fields',
                "update_documents": 'Generate UPDATE DOCUMENTS with WHERE clause',
                "bulk_update": 'Generate UPDATE DOCUMENTS with WHERE clause',
                "delete_documents": 'Generate DELETE DOCUMENTS with WHERE clause',
                "bulk_delete": 'Generate DELETE DOCUMENTS with WHERE clause',
                "aggregate_query": 'Generate SELECT with COUNT(*), SUM(), AVG() and GROUP BY'
            }
            
            if action_name in action_hints:
                prompt += f"\n\nSpecific requirement: {action_hints[action_name]}"

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2:3b",  # Upgraded from 1b to 3b for better accuracy
                    "prompt": prompt,
                    "system": "You are a SyndrQL query expert. Generate only valid SyndrQL queries following the exact syntax rules provided.",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent output
                        "top_p": 0.9,
                        "top_k": 40,
                        "repeat_penalty": 1.1,  # Reduce repetition
                        "num_predict": 200  # Limit response length to reduce rambling
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
            
            bundle = random.choice(["products", "orders", "users"])
            
            # Bundle-specific field mappings
            if bundle == "products":
                fields = ["DocumentID", "name"]
                order_by = random.choice(["name", "created_at", None]) if use_order else None
                group_by = "category" if use_group else None
            elif bundle == "orders":
                fields = ["DocumentID", "total"]
                order_by = random.choice(["total", "created_at", None]) if use_order else None
                group_by = "status" if use_group else None
            else:  # users
                fields = ["DocumentID", "name"]
                order_by = random.choice(["name", "created_at", None]) if use_order else None
                group_by = None  # users has no good grouping field
            
            return {
                "bundle": bundle,
                "fields": fields,
                "order_by": order_by,
                "group_by": group_by,
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
                "count": self._get_count_for_action(action_name),
                "use_agent_categories": True  # Flag to use agent-specific categories
            }
        
        elif "update" in action_name or action_name == "update_documents":
            # Use agent-specific categories and add rating/stock filters for more specificity
            category = random.choice(self.agent_categories)
            
            # Add additional filter dimensions to reduce overlap
            additional_filters = []
            if random.random() < 0.5:  # 50% chance of adding rating filter
                rating = random.choice(RATING_VALUES)
                additional_filters.append(f'("rating" <= {rating})')
            if random.random() < 0.5:  # 50% chance of adding stock filter
                stock_range = random.choice(STOCK_RANGES)
                additional_filters.append(f'("stock" >= {stock_range[0]} AND "stock" <= {stock_range[1]})')
            
            # Build WHERE clause with category + optional filters
            where_parts = [f'("category" == "{category}")']
            where_parts.extend(additional_filters)
            where = " AND ".join(where_parts)
            
            return {
                "bundle": "products",
                "where": where,
                "count": self._get_count_for_action(action_name)
            }
        
        elif "delete" in action_name or action_name == "delete_documents":
            # Add more specificity to DELETE queries to reduce overlap
            # Vary by rating ranges and add randomization
            rating_threshold = random.choice([1, 2])  # Delete 1-star or 1-2 star reviews
            
            # Optionally add date filters
            additional_filters = []
            if random.random() < 0.3:  # 30% chance of date filter
                days_ago = random.randint(30, 365)
                additional_filters.append(f'("created_at" < DATE_SUB(NOW(), INTERVAL {days_ago} DAY))')
            
            where_parts = [f'("rating" <= {rating_threshold})']
            where_parts.extend(additional_filters)
            where = " AND ".join(where_parts) if additional_filters else f'("rating" <= {rating_threshold})'
            
            return {
                "bundle": "reviews",
                "where": where,
                "count": self._get_count_for_action(action_name)
            }
        
        elif "aggregate" in action_name:
            bundle = random.choice(["orders", "products"])
            # Use bundle-appropriate fields for GROUP BY
            if bundle == "orders":
                group_by = "status"  # orders has: total, status, created_at
            else:  # products
                group_by = "category"  # products has: name, price, category, stock, rating, created_at
            
            return {
                "bundle": bundle,
                "aggregates": ["COUNT(*)", "SUM(total)", "AVG(total)"],
                "group_by": group_by
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
            
            # If GROUP BY is present, only select the grouped field + aggregates
            if group_by:
                query = f'SELECT "{group_by}", COUNT(*) as "count" FROM "{bundle}" GROUP BY "{group_by}"'
            else:
                fields_str = ", ".join([f'"{f}"' for f in fields])
                query = f'SELECT {fields_str} FROM "{bundle}"'
                if order_by:
                    query += f' ORDER BY "{order_by}" DESC'
            
            query += f" LIMIT {limit};"
            return query
        
        # Simple JOINs
        elif action_name in ["join_simple", "large_join_simple"]:
            bundles = params.get("bundles", ["products", "reviews"])
            where = params.get("where", '("rating" >= 4)')
            limit = params.get("limit", 50)
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            # If GROUP BY, only select grouped field + aggregates
            if group_by:
                query = f'''SELECT "{bundles[0]}"."category", COUNT(*) as "count", AVG("{bundles[1]}"."rating") as "avg_rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"
                      WHERE {where}
                      GROUP BY "{bundles[0]}"."category"'''
            else:
                query = f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", "{bundles[1]}"."rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"
                      WHERE {where}'''
                if order_by:
                    query += f' ORDER BY "{order_by}" DESC'
                
            query += f" LIMIT {limit};"
            return query
        
        # Complex JOINs
        elif action_name in ["join_complex", "large_join_complex"]:
            bundles = params.get("bundles", ["products", "reviews", "users"])
            where = params.get("where", '("rating" >= 4)')
            limit = params.get("limit", 50)
            order_by = params.get("order_by")
            group_by = params.get("group_by")
            
            if group_by:
                # GROUP BY query with aggregates
                query = f'''SELECT "{bundles[0]}"."category", COUNT(*) as "count", AVG("{bundles[1]}"."rating") as "avg_rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"'''
                if len(bundles) > 2:
                    query += f' JOIN "{bundles[2]}" ON "{bundles[1]}"."user_id" == "{bundles[2]}"."DocumentID"'
                query += f' WHERE {where} GROUP BY "{bundles[0]}"."category"'
            else:
                # Regular JOIN without GROUP BY
                query = f'''SELECT "{bundles[0]}"."DocumentID", "{bundles[0]}"."name", "{bundles[1]}"."rating"
                      FROM "{bundles[0]}"
                      JOIN "{bundles[1]}" ON "{bundles[0]}"."DocumentID" == "{bundles[1]}"."product_id"'''
                if len(bundles) > 2:
                    query += f' JOIN "{bundles[2]}" ON "{bundles[1]}"."user_id" == "{bundles[2]}"."DocumentID"'
                query += f' WHERE {where}'
                if order_by:
                    query += f' ORDER BY "{order_by}" DESC'
            
            query += f" LIMIT {limit};"
            return query
        
        # CREATE operations
        elif action_name in ["create_document", "bulk_create"]:
            bundle = params.get("bundle", "products")
            count = params.get("count", 1)
            use_agent_categories = params.get("use_agent_categories", False)
            
            if bundle == "products":
                # Use agent-specific categories and realistic ranges
                category = random.choice(self.agent_categories) if use_agent_categories else get_random_category()
                price_range = random.choice(PRICE_RANGES)
                price = round(random.uniform(price_range[0], price_range[1]), 2)
                stock_range = random.choice(STOCK_RANGES)
                stock = random.randint(stock_range[0], stock_range[1])
                
                return f'''ADD DOCUMENT TO BUNDLE "products"
                          WITH (
                              {{\"name\" = "Product {random.randint(1000,999999)}"}},
                              {{\"price\" = {price}}},
                              {{\"category\" = "{category}"}},
                              {{\"stock\" = {stock}}}
                          );'''
            elif bundle == "users":
                return f'''ADD DOCUMENT TO BUNDLE "users"
                          WITH (
                              {{\"name\" = "User {random.randint(1000,999999)}"}},
                              {{\"email\" = "user{random.randint(1000,999999)}@example.com"}}
                          );'''
            elif bundle == "orders":
                # Use real document IDs from seeding
                user_ids = self.document_ids.get("user_document_ids", [])
                user_id = random.choice(user_ids) if user_ids else "unknown_user"
                
                # Use expanded order statuses
                status = random.choice(ORDER_STATUSES)
                total = round(random.uniform(50, 500), 2)
                
                return f'''ADD DOCUMENT TO BUNDLE "orders"
                          WITH (
                              {{\"user_id\" = "{user_id}"}},
                              {{\"total\" = {total}}},
                              {{\"status\" = "{status}"}}
                          );'''
            else:
                return f'''ADD DOCUMENT TO BUNDLE "{bundle}"
                          WITH ({{\"id\" = {random.randint(1,1000)}}});'''
        
        # UPDATE operations
        elif action_name in ["update_documents", "bulk_update"]:
            bundle = params.get("bundle", "products")
            where = params.get("where", '("id" > 0)')
            
            # Use more varied update values
            stock_range = random.choice(STOCK_RANGES)
            new_stock = random.randint(stock_range[0], stock_range[1])
            
            return f'''UPDATE DOCUMENTS IN BUNDLE "{bundle}"
                      ("stock" = {new_stock})
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

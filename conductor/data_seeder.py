# firestorm/conductor/data_seeder.py
import random
import logging
import json
from datetime import datetime, timedelta
from faker import Faker
from conductor.expanded_categories import (
    PRODUCT_CATEGORIES, 
    RATING_VALUES, 
    STOCK_RANGES, 
    PRICE_RANGES,
    ORDER_STATUSES
)

logger = logging.getLogger(__name__)

class DataSeeder:
    """Seeds test data into SyndrDB using Faker for realistic data with high entropy"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.faker = Faker()
        
        # Use expanded 350+ categories for maximum entropy
        self.categories = PRODUCT_CATEGORIES
        
        # Use expanded order statuses for more variety
        self.order_statuses = ORDER_STATUSES
        
        # Store parent DocumentIDs for foreign key relationships
        self.user_doc_ids = []
        self.product_doc_ids = []
        self.order_doc_ids = []
    
    def seed_users(self, count: int):
        """Seed user accounts and capture their DocumentIDs for foreign key relationships"""
        logger.info(f"Seeding {count} users...")
        
        # Clear existing user IDs if reseeding
        if len(self.user_doc_ids) > 1000:
            self.user_doc_ids = self.user_doc_ids[-100:]
        
        batch_size = 100
        for i in range(0, count, batch_size):
            batch = min(batch_size, count - i)
            self._seed_users_batch(batch)
        
        logger.info(f"✓ Seeded {count} users. Tracking {len(self.user_doc_ids)} DocumentIDs for relationships")
    
    def _seed_users_batch(self, count: int):
        """Seed a batch of users with realistic data from Faker"""
        for i in range(count):
            name = self.faker.name()
            # Generate unique email based on name
            email = self.faker.email()
            created = self.faker.date_time_between(start_date='-2y', end_date='now').isoformat()
            last_login = self.faker.date_time_between(start_date='-30d', end_date='now').isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "users"
                       WITH (
                           {{"name" = "{name}"}},
                           {{"email" = "{email}"}},
                           {{"created_at" = "{created}"}},
                           {{"last_login" = "{last_login}"}}
                       );'''
            
            result = self.db.execute(query)
            
            # Capture DocumentID from successful insert
            # Server response structure: {"ExecutionTimeMS": 58.56, "Result": "{\"DocumentID\": \"...\", ...}", "ResultCount": 1}
            try:
                if not result.get("success"):
                    logger.error(f"Failed to insert user: {result.get('error', 'Unknown error')}")
                    continue
                
                doc_id = None
                server_response = result.get("result", {})
                
                # Result field contains JSON string with DocumentID
                if "Result" in server_response:
                    result_str = server_response["Result"]
                    if isinstance(result_str, str):
                        try:
                            parsed = json.loads(result_str)
                            doc_id = parsed.get("DocumentID")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error(f"Failed to parse Result field: {e}")
                
                if doc_id:
                    self.user_doc_ids.append(doc_id)
                    if len(self.user_doc_ids) > 20:
                        self.user_doc_ids.pop(0)
                else:
                    logger.error(f"Could not extract DocumentID from user insert. Response: {json.dumps(result, indent=2)[:300]}")
            except Exception as e:
                logger.error(f"Exception extracting DocumentID from user insert: {e}")
    
    def seed_products(self, count: int):
        """Seed products with realistic names and high entropy data"""
        logger.info(f"Seeding {count} products...")
        
        # Clear existing product IDs if reseeding
        if len(self.product_doc_ids) > 1000:
            self.product_doc_ids = self.product_doc_ids[-100:]
        
        for i in range(count):
            # Generate realistic product names
            name = self.faker.catch_phrase()
            
            # Use more granular price ranges for variety
            price_range = random.choice(PRICE_RANGES)
            price = round(random.uniform(price_range[0], price_range[1]), 2)
            
            # Use expanded 350+ categories
            category = random.choice(self.categories)
            
            # Use more granular stock ranges
            stock_range = random.choice(STOCK_RANGES)
            stock = random.randint(stock_range[0], stock_range[1])
            
            # Use discrete rating values for better variety
            rating = random.choice(RATING_VALUES)
            created = self.faker.date_time_between(start_date='-2y', end_date='now').isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "products"
                       WITH (
                           {{"name" = "{name}"}},
                           {{"price" = {price}}},
                           {{"category" = "{category}"}},
                           {{"stock" = {stock}}},
                           {{"rating" = {rating}}},
                           {{"created_at" = "{created}"}}
                       );'''
            
            result = self.db.execute(query)
            
            # Capture DocumentID from successful insert
            # Server response structure: {"ExecutionTimeMS": 58.56, "Result": "{\"DocumentID\": \"...\", ...}", "ResultCount": 1}
            try:
                if not result.get("success"):
                    logger.error(f"Failed to insert product: {result.get('error', 'Unknown error')}")
                    continue
                
                doc_id = None
                server_response = result.get("result", {})
                
                # Result field contains JSON string with DocumentID
                if "Result" in server_response:
                    result_str = server_response["Result"]
                    if isinstance(result_str, str):
                        try:
                            parsed = json.loads(result_str)
                            doc_id = parsed.get("DocumentID")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error(f"Failed to parse Result field: {e}")
                
                if doc_id:
                    self.product_doc_ids.append(doc_id)
                    if len(self.product_doc_ids) > 20:
                        self.product_doc_ids.pop(0)
                else:
                    logger.error(f"Could not extract DocumentID from product insert. Response: {json.dumps(result, indent=2)[:300]}")
            except Exception as e:
                logger.error(f"Exception extracting DocumentID from product insert: {e}")
        
        logger.info(f"✓ Seeded {count} products. Tracking {len(self.product_doc_ids)} DocumentIDs for relationships")
    
    def seed_orders(self, count: int):
        """Seed historical orders using real user DocumentIDs from relationships"""
        logger.info(f"Seeding {count} orders...")
        
        if not self.user_doc_ids:
            logger.warning("No user DocumentIDs available! Seeding users first...")
            self.seed_users(count=20)
        
        # Clear existing order IDs if reseeding
        if len(self.order_doc_ids) > 1000:
            self.order_doc_ids = self.order_doc_ids[-100:]
        
        for i in range(count):
            # Use a real user DocumentID from the relationship
            user_id = random.choice(self.user_doc_ids)
            total = round(random.uniform(10.0, 500.0), 2)
            status = random.choice(self.order_statuses)
            created = self.faker.date_time_between(start_date='-1y', end_date='now').isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "orders"
                       WITH (
                           {{"user_id" = "{user_id}"}},
                           {{"total" = {total}}},
                           {{"status" = "{status}"}},
                           {{"created_at" = "{created}"}}
                       );'''
            
            result = self.db.execute(query)
            
            # Capture DocumentID for order_items relationship
            # Server response structure: {"ExecutionTimeMS": 58.56, "Result": "{\"DocumentID\": \"...\", ...}", "ResultCount": 1}
            try:
                if not result.get("success"):
                    logger.error(f"Failed to insert order: {result.get('error', 'Unknown error')}")
                    continue
                
                doc_id = None
                server_response = result.get("result", {})
                
                # Result field contains JSON string with DocumentID
                if "Result" in server_response:
                    result_str = server_response["Result"]
                    if isinstance(result_str, str):
                        try:
                            parsed = json.loads(result_str)
                            doc_id = parsed.get("DocumentID")
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.error(f"Failed to parse Result field: {e}")
                
                if doc_id:
                    self.order_doc_ids.append(doc_id)
                    if len(self.order_doc_ids) > 20:
                        self.order_doc_ids.pop(0)
                else:
                    logger.error(f"Could not extract DocumentID from order insert. Response: {json.dumps(result, indent=2)[:300]}")
            except Exception as e:
                logger.error(f"Exception extracting DocumentID from order insert: {e}")
        
        logger.info(f"✓ Seeded {count} orders. Tracking {len(self.order_doc_ids)} DocumentIDs for relationships")
    
    def seed_reviews(self, count: int):
        """Seed product reviews using real user and product DocumentIDs from relationships"""
        logger.info(f"Seeding {count} reviews...")
        
        if not self.user_doc_ids:
            logger.warning("No user DocumentIDs available! Seeding users first...")
            self.seed_users(count=20)
        
        if not self.product_doc_ids:
            logger.warning("No product DocumentIDs available! Seeding products first...")
            self.seed_products(count=20)
        
        for i in range(count):
            # Use real DocumentIDs from relationships
            user_id = random.choice(self.user_doc_ids)
            product_id = random.choice(self.product_doc_ids)
            rating = random.randint(1, 5)
            # Generate realistic review text based on rating
            if rating >= 4:
                comment = self.faker.sentence(nb_words=random.randint(5, 15))
            elif rating == 3:
                comment = self.faker.sentence(nb_words=random.randint(5, 12))
            else:
                comment = self.faker.sentence(nb_words=random.randint(4, 10))
            
            created = self.faker.date_time_between(start_date='-1y', end_date='now').isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "reviews"
                       WITH (
                           {{"user_id" = "{user_id}"}},
                           {{"product_id" = "{product_id}"}},
                           {{"rating" = {rating}}},
                           {{"comment" = "{comment}"}},
                           {{"created_at" = "{created}"}}
                       );'''
            
            self.db.execute(query)
        
        logger.info(f"✓ Seeded {count} reviews")
    
    def seed_order_items(self, count: int):
        """Seed order items using real order and product DocumentIDs from relationships"""
        logger.info(f"Seeding {count} order items...")
        
        if not self.order_doc_ids:
            logger.warning("No order DocumentIDs available! Seeding orders first...")
            self.seed_orders(count=20)
        
        if not self.product_doc_ids:
            logger.warning("No product DocumentIDs available! Seeding products first...")
            self.seed_products(count=20)
        
        for i in range(count):
            # Use real DocumentIDs from relationships
            order_id = random.choice(self.order_doc_ids)
            product_id = random.choice(self.product_doc_ids)
            quantity = random.randint(1, 5)
            price = round(random.uniform(5.0, 500.0), 2)
            
            query = f'''ADD DOCUMENT TO BUNDLE "order_items"
                       WITH (
                           {{"order_id" = "{order_id}"}},
                           {{"product_id" = "{product_id}"}},
                           {{"quantity" = {quantity}}},
                           {{"price" = {price}}}
                       );'''
            
            self.db.execute(query)
        
        logger.info(f"✓ Seeded {count} order items")
    
    def seed_cart_items(self, count: int):
        """Seed cart items using real user and product DocumentIDs from relationships"""
        logger.info(f"Seeding {count} cart items...")
        
        if not self.user_doc_ids:
            logger.warning("No user DocumentIDs available! Seeding users first...")
            self.seed_users(count=20)
        
        if not self.product_doc_ids:
            logger.warning("No product DocumentIDs available! Seeding products first...")
            self.seed_products(count=20)
        
        for i in range(count):
            # Use real DocumentIDs from relationships
            user_id = random.choice(self.user_doc_ids)
            product_id = random.choice(self.product_doc_ids)
            quantity = random.randint(1, 3)
            
            query = f'''ADD DOCUMENT TO BUNDLE "cart_items"
                       WITH (
                           {{"user_id" = "{user_id}"}},
                           {{"product_id" = "{product_id}"}},
                           {{"quantity" = {quantity}}}
                       );'''
            
            self.db.execute(query)
        
        logger.info(f"✓ Seeded {count} cart items")
    
    def get_document_ids(self) -> dict:
        """
        Return captured DocumentIDs for use in query generation.
        
        Returns:
            Dict with user_document_ids, product_document_ids, order_document_ids
        """
        return {
            "user_document_ids": self.user_doc_ids.copy(),
            "product_document_ids": self.product_doc_ids.copy(),
            "order_document_ids": self.order_doc_ids.copy()
        }
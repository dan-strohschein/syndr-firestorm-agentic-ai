# firestorm/conductor/conductor.py
import logging
import time
import threading
from typing import List, Dict, Any
from tools.syndrdb_client import SyndrDBClient
from conductor.data_seeder import DataSeeder
from conductor.health_monitor import HealthMonitor

logger = logging.getLogger(__name__)

class FirestormConductor:
    """Main conductor for Firestorm load testing"""
    
    def __init__(self, syndrdb_host: str = "127.0.0.1", syndrdb_port: int = 1776, 
                 username: str = "root", password: str = "root", database: str = "primary"):
        # Use connection string format
        conn_str = f"syndrdb://{syndrdb_host}:{syndrdb_port}:{database}:{username}:{password}"
        self.db_client = SyndrDBClient(conn_str)
        self.data_seeder = DataSeeder(self.db_client)
        self.health_monitor = HealthMonitor(self.db_client)
        
        self.test_database = database
        self.min_products = 5000
        self.min_users = 10000
        self.min_orders = 5000
        self.min_reviews = 10000
        
        # Store DocumentIDs from seeding for query generation
        self.document_ids = {}
        
        # Target bundle counts
        self.target_counts = {
            "users": self.min_users,
            "products": self.min_products,
            "orders": self.min_orders,
            "reviews": self.min_reviews,
            "order_items": 0,
            "cart_items": 0
        }
        
    def _check_database_exists(self) -> bool:
        """Check if test database exists"""
        logger.info("Checking if database exists...")
        logger.info("Executing: SHOW DATABASES;")
        result = self.db_client.execute('SHOW DATABASES;')
        logger.info(f"Got result: {result}")
        
        if not result.get("success"):
            logger.error(f"Failed to check databases: {result.get('error')}")
            return False
        
        # Result is an array of database names
        result_data = result.get("result", {})
        databases = result_data.get("Result", [])
        logger.info(f"Existing databases: {databases}")
        
        return self.test_database in databases
    
    def _use_database(self):
        """Switch to the test database"""
        use_query = f'USE "{self.test_database}";'
        result = self.db_client.execute(use_query)
        
        if result.get("success"):
            logger.info(f"Switched to database: {self.test_database}")
        else:
            logger.error(f"Failed to switch to database: {result.get('error')}")
    
    def _check_and_populate_bundles(self):
        """Check if bundles exist and populate if needed"""
        result = self.db_client.execute('SHOW BUNDLES;')
        
        if not result.get("success"):
            logger.error(f"Failed to check bundles: {result.get('error')}")
            self._create_bundles()
            self._seed_data()
            self._create_indexes()
            return
        
        bundles_info = result.get("result", {})
        bundles_str = str(bundles_info)
        logger.info(f"Existing bundles: {bundles_info}")
        
        required_bundles = ["users", "products", "orders", "order_items", "cart_items", "reviews"]
        missing_bundles = [b for b in required_bundles if b not in bundles_str]
        
        if missing_bundles:
            logger.info(f"Missing bundles: {missing_bundles}. Creating all bundles...")
            self._create_bundles()
            self._seed_data()
            self._create_indexes()
        else:
            logger.info("All bundles exist. Checking document counts...")
            self._check_and_refill_data()
    
    def _check_and_refill_data(self):
        """Check document counts and refill if needed"""
        for bundle_name, target_count in self.target_counts.items():
            if target_count == 0:
                continue
            
            count_query = f'SELECT COUNT(*) FROM "{bundle_name}";'
            result = self.db_client.execute(count_query)
            
            if not result.get("success"):
                logger.warning(f"Failed to count {bundle_name}: {result.get('error')}")
                continue
            
            # Extract count from Column1 in Result array
            result_data = result.get("result", {})
            result_array = result_data.get("Result", [])
            current_count = result_array[0].get("Column1", 0) if result_array else 0
            logger.info(f"Bundle '{bundle_name}': {current_count} / {target_count} documents")
            
            if current_count < target_count:
                needed = target_count - current_count
                logger.info(f"Adding {needed} documents to '{bundle_name}'...")
                
                if bundle_name == "users":
                    self.data_seeder.seed_users(count=needed)
                elif bundle_name == "products":
                    self.data_seeder.seed_products(count=needed)
                elif bundle_name == "orders":
                    self.data_seeder.seed_orders(count=needed)
                elif bundle_name == "reviews":
                    self.data_seeder.seed_reviews(count=needed)
        
        # Capture DocumentIDs after refilling
        self.document_ids = self.data_seeder.get_document_ids()
        logger.info(f"✓ Captured {len(self.document_ids.get('user_document_ids', []))} user IDs, "
                   f"{len(self.document_ids.get('product_document_ids', []))} product IDs, "
                   f"{len(self.document_ids.get('order_document_ids', []))} order IDs for query generation")
    
    def setup_test_environment(self):
        """Set up test database and initial data"""
        logger.info("🔥 Firestorm Conductor: Setting up test environment...")
        
        # Use a dedicated test database instead of primary
        self.test_database = "firestorm_test"
        logger.info(f"Using test database: {self.test_database}")
        
        db_exists = self._check_database_exists()
        
        # Always switch to the test database context
        if db_exists:
            self._use_database()
        # Always switch to the test database context
        if db_exists:
            self._use_database()
        
        if not db_exists:
            logger.info(f"Database '{self.test_database}' does not exist, creating...")
            self._create_database()
            self._create_bundles()
            self._seed_data()
            self._create_indexes()
        else:
            logger.info(f"Database '{self.test_database}' already exists")
            self._check_and_populate_bundles()
        
        self._verify_setup()
        logger.info("✅ Test environment ready!")
    
    def _create_database(self):
        """Create test database"""
        query = f'CREATE DATABASE "{self.test_database}";'
        result = self.db_client.execute(query)
        
        if result.get("success"):
            logger.info(f"✓ Created database: {self.test_database}")
        else:
            logger.error(f"Failed to create database: {result.get('error')}")
            return
        
        self._use_database()
    
    def _create_bundles(self):
        """Create all necessary bundles"""
        bundles = {
            "users": '''CREATE BUNDLE "users"
                       WITH FIELDS (
                           {"name", "STRING", true, false, ""},
                           {"email", "STRING", true, true, ""},
                           {"created_at", "STRING", false, false, ""},
                           {"last_login", "STRING", false, false, ""}
                       );''',
                       


           "products": '''CREATE BUNDLE "products"
                         WITH FIELDS (
                             {"name", "STRING", true, false, ""},
                             {"price", "FLOAT", true, false, 0.0},
                             {"category", "STRING", true, false, ""},
                             {"stock", "INT", true, false, 0},
                             {"rating", "FLOAT", false, false, 0.0},
                             {"created_at", "STRING", false, false, ""}
                         );''',
 
            "orders": '''CREATE BUNDLE "orders"
                        WITH FIELDS (
                            {"total", "FLOAT", true, false, 0.0},
                            {"status", "STRING", true, false, "pending"},
                            {"created_at", "STRING", false, false, ""}
                        );''',
         
            "order_items": '''CREATE BUNDLE "order_items"
                             WITH FIELDS (
                                 {"quantity", "INT", true, false, 1},
                                 {"price", "FLOAT", true, false, 0.0}
                             );''',
            
            "cart_items": '''CREATE BUNDLE "cart_items"
                            WITH FIELDS (
                                {"quantity", "INT", true, false, 1}
                            );''',
            
            "reviews": '''CREATE BUNDLE "reviews"
                         WITH FIELDS (                          
                             {"rating", "INT", true, false, 5},
                             {"comment", "STRING", false, false, ""},
                             {"created_at", "STRING", false, false, ""}
                         );''',
                         
            "rel1" : '''UPDATE BUNDLE "users"
ADD RELATIONSHIP ("users_orders" {"1toMany", "users", "DocumentID", "orders", "user_id"});''',
            "rel2" : ''' UPDATE BUNDLE "users"
ADD RELATIONSHIP ("users_cartItem" {"1toMany", "users", "DocumentID", "cart_items", "user_id"});''',
             "rel3" : '''UPDATE BUNDLE "users"
ADD RELATIONSHIP ("users_reviews" {"1toMany", "users", "DocumentID", "reviews", "user_id"});''',


        "rel4" : '''UPDATE BUNDLE "products"
ADD RELATIONSHIP ("products_OI" {"1toMany", "products", "DocumentID", "order_items", "product_id"});''',
       "rel5" : ''' UPDATE BUNDLE "products"
ADD RELATIONSHIP ("products_cartItem" {"1toMany", "products", "DocumentID", "cart_items", "product_id"});''',
        "rel6" : '''UPDATE BUNDLE "products"
ADD RELATIONSHIP ("products_reviews" {"1toMany", "products", "DocumentID", "reviews", "product_id"});''',
     
              "rel7" : '''UPDATE BUNDLE "orders"
ADD RELATIONSHIP ("orders_OI" {"1toMany", "orders", "DocumentID", "order_items", "order_id"});'''
            
         
        }
        
        for bundle_name, create_query in bundles.items():
            result = self.db_client.execute(create_query)
            if result.get("success"):
                logger.info(f"✓ Created bundle: {bundle_name}")
            else:
                logger.warning(f"Bundle {bundle_name} may exist: {result.get('error')}")
    
    def _seed_data(self):
        """Seed initial data in proper order to respect relationships"""
        logger.info("Seeding data with proper relationship hierarchy...")
        
        # Seed parent bundles first to capture DocumentIDs
        self.data_seeder.seed_users(count=self.min_users)
        self.data_seeder.seed_products(count=self.min_products)
        
        # Seed child bundles using parent DocumentIDs
        self.data_seeder.seed_orders(count=self.min_orders)
        self.data_seeder.seed_reviews(count=self.min_reviews)
        
        # Seed additional relationship data
        logger.info("Seeding order_items and cart_items...")
        self.data_seeder.seed_order_items(count=self.min_orders * 2)  # ~2 items per order
        self.data_seeder.seed_cart_items(count=self.min_users // 5)  # ~20% of users have cart items
        
        # Capture DocumentIDs for query generation
        self.document_ids = self.data_seeder.get_document_ids()
        logger.info(f"✓ Data seeding complete. Captured {len(self.document_ids.get('user_document_ids', []))} user IDs, "
                   f"{len(self.document_ids.get('product_document_ids', []))} product IDs, "
                   f"{len(self.document_ids.get('order_document_ids', []))} order IDs for query generation")
    
    
    def _create_indexes(self):
        """Create indexes for performance"""
        indexes = [
            '''CREATE B-INDEX "idx_products_category" ON BUNDLE "products" 
               WITH FIELDS (
                   {"category", false, false}
               );''',
            '''CREATE B-INDEX "idx_products_price" ON BUNDLE "products" 
               WITH FIELDS (
                   {"price", false, false}
               );''',
            '''CREATE HASH INDEX "idx_users_email" ON BUNDLE "users" 
               WITH FIELDS (
                   {"email", false, true}
               );''',
            '''CREATE B-INDEX "idx_orders_user" ON BUNDLE "orders" 
               WITH FIELDS (
                   {"user_id", false, false}
               );''',
        ]
        
        for idx_query in indexes:
            result = self.db_client.execute(idx_query)
            if result.get("success"):
                logger.info(f"✓ Created index")
    
    def _verify_setup(self):
        """Verify environment is ready"""
        result = self.db_client.execute('SELECT COUNT(*) FROM "products";')
        result_data = result.get("result", {})
        result_array = result_data.get("Result", [])
        product_count = result_array[0].get("Column1", 0) if result_array else 0
        
        if product_count < self.min_products:
            logger.warning(f"Low product count: {product_count}")
        else:
            logger.info(f"✓ Products: {product_count}")
    
    def monitor_health(self, interval_seconds: int = 5):
        """Monitor SyndrDB health during test"""
        while True:
            metrics = self.health_monitor.collect_metrics()
            logger.info(f"Health: {metrics}")
            time.sleep(interval_seconds)
    
    def maintain_data_levels(self, interval_seconds: int = 60):
        """Keep data levels topped up during test"""
        while True:
            result = self.db_client.execute('SELECT COUNT(*) FROM "products";')
            result_data = result.get("result", {})
            result_array = result_data.get("Result", [])
            count = result_array[0].get("Column1", 0) if result_array else 0
            
            if count < self.min_products * 0.8:
                logger.warning(f"Refilling products (current: {count})")
                self.data_seeder.seed_products(count=1000)
            
            time.sleep(interval_seconds)
    
    def pregenerate_queries_for_agents(self, agents: List, ollama_url: str = "http://localhost:11434"):
        """
        Pre-generate queries for all agents before testing.
        
        Args:
            agents: List of agent instances
            ollama_url: Ollama API URL
        """
        from agents.query_generator import QueryGenerator
        
        logger.info("=" * 80)
        logger.info("🔥 PRE-GENERATING QUERIES FOR AGENTS")
        logger.info("=" * 80)
        
        if not self.document_ids:
            logger.warning("No DocumentIDs available! Using empty arrays for query generation")
            self.document_ids = {
                "user_document_ids": [],
                "product_document_ids": [],
                "order_document_ids": []
            }
        
        total_queries_generated = 0
        generation_start = time.time()
        
        for agent in agents:
            logger.info(f"\nGenerating queries for {agent.agent_id} ({agent.persona_name})...")
            
            try:
                # Create query generator for this agent
                generator = QueryGenerator(
                    persona_name=agent.persona_name,
                    agent_id=agent.agent_id,
                    document_ids=self.document_ids,
                    ollama_url=ollama_url
                )
                
                # Generate 200-300 queries
                queries = generator.generate_queries()
                
                # Store in agent
                agent.pregenerated_queries = queries
                total_queries_generated += len(queries)
                
                logger.info(
                    f"✓ {agent.agent_id} ({agent.persona_name}): "
                    f"Generated {len(queries)} queries"
                )
                
            except RuntimeError as e:
                # Failure rate exceeded 25%
                logger.error(f"Query generation failed for {agent.agent_id}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error generating queries for {agent.agent_id}: {e}")
                raise
        
        generation_duration = time.time() - generation_start
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ QUERY GENERATION COMPLETE")
        logger.info(f"   Total queries: {total_queries_generated}")
        logger.info(f"   Agents: {len(agents)}")
        logger.info(f"   Duration: {generation_duration:.1f} seconds")
        logger.info(f"   Avg per agent: {total_queries_generated / len(agents):.0f} queries")
        logger.info("=" * 80 + "\n")
        
        return total_queries_generated

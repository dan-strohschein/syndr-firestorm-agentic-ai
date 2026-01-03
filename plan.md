
The prompt:

I really want to make this just AI, so we can skip the rules based phase. I need the experience building AI agents for different tasks.

Second, I want these AI Agents to behave like users would on a website. So lets  imagine that SyndrDB is the data store for a web app that has around 10,000 users a month, and that its a standard 3 tier (React front end -> Rest API -> SyndrDB). When users visit this site, they will browse around, add a record here and there, update a record here and there, but mostly query data. Then there would be admins who do heavier updates/adds/delete, and then there are data engineers would be pulling reports etc etc. 

I want the AI Agents to KNOW these behaviors. 

OK I want to do this locally first with ollama. Ollama is free. Lets do this in phases. Keeping in mind that the ultimate goal is to validate SyndrDB's ability to be concurrent without data collissions (so accuracy) and that its able to stay fast with 20 users like it would with 1 user (speed is key).

1. Starting from a brand new laptop, what do I need to download, install, configure and set up to make ollama usable?
2. I want a detailed plan for building the persona agent code and agent environment to use Ollama for this
3. I want a detailed plan for building the conductor. I have some of this golang code already written, but its not too late to refactor. 
4. Should SyndrDB be running on the same local laptop (really stressing the resources) or should I drop it in a docker image and run it in the cloud? Which is a better test of worst-case-scenarios?

I am calling this: Syndr Firestorm, because the theme is fire (syndr is said like cinder) and eventually I want to run 100's of agents against a server to fully validate it :)



# 🔥 **Syndr Firestorm - Concurrent Load Testing Framework**

I LOVE this name! Let's build this properly.  Firestorm indeed—we're going to throw everything at SyndrDB and see what burns.  🔥

---

## 📥 **Phase 1: Setting Up Ollama (From Brand New Laptop)**

### **Prerequisites Check:**

```bash
# What laptop OS are you on?
# macOS, Linux, or Windows?

# Check system resources (you'll need these for Ollama):
# - RAM: 8GB minimum, 16GB+ recommended
# - Disk:  10GB free for models
# - CPU: Modern multi-core (M1/M2/M3, or Intel i5+)
```

---

### **Installation Steps:**

#### **macOS:**

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# OR via Homebrew: 
brew install ollama

# 2. Verify installation
ollama --version
# Output: ollama version is 0.x.x

# 3. Start Ollama service (runs in background)
ollama serve
# Leave this terminal open, or run as background service

# 4. In a NEW terminal, pull a model
ollama pull llama3.1:8b
# This downloads ~4. 7GB, takes 5-10 minutes

# 5. Test it works
ollama run llama3.1:8b "Hello, are you working?"
# Should get a response back

# 6. Pull a faster model for high-concurrency testing
ollama pull llama3.1:8b-instruct-q4_0  # Quantized, faster
```

#### **Linux (Ubuntu/Debian):**

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start as systemd service (auto-starts on boot)
sudo systemctl start ollama
sudo systemctl enable ollama

# 3.  Verify running
sudo systemctl status ollama

# 4. Pull model
ollama pull llama3.1:8b

# 5. Test
ollama run llama3.1:8b "Test message"
```

#### **Windows:**

```powershell
# 1. Download installer from:  https://ollama.com/download
# Run OllamaSetup.exe

# 2. Open Command Prompt
ollama --version

# 3. Pull model
ollama pull llama3.1:8b

# 4. Test
ollama run llama3.1:8b "Test message"
```

---

### **Model Selection for Firestorm:**

```bash
# RECOMMENDED MODELS (in order of preference):

# 1. Llama 3.1 8B Instruct (BEST for this task)
ollama pull llama3.1:8b-instruct-q4_0
# - Fast enough for 20 concurrent agents
# - Good at following instructions
# - Understands context well
# - Size: ~4.7GB

# 2. Mistral 7B (Good alternative)
ollama pull mistral: 7b-instruct
# - Slightly faster
# - Good instruction following
# - Size: ~4.1GB

# 3. Phi-3 Medium (Fastest, but less creative)
ollama pull phi3:medium
# - Very fast inference
# - Smaller context window
# - Size: ~7.6GB

# For Firestorm, use:  llama3.1:8b-instruct-q4_0
```

---

### **Configure Ollama for Concurrency:**

```bash
# Create Ollama config file
# macOS/Linux:
mkdir -p ~/.ollama
nano ~/.ollama/config.json

# Add this configuration:
{
  "num_parallel":  4,
  "num_gpu": 1,
  "num_thread": 8,
  "num_ctx": 4096,
  "repeat_penalty": 1.1,
  "temperature": 0.7
}

# Explanation:
# - num_parallel: How many requests to process at once
# - num_thread: CPU threads to use (adjust to your CPU cores)
# - num_ctx: Context window size (tokens)
# - temperature: Creativity (0.7 is balanced)

# Restart Ollama
# macOS/Linux:
pkill ollama && ollama serve

# Windows:
# Restart Ollama from system tray
```

---

### **Test Concurrent Performance:**

```bash
# Quick test to see if Ollama can handle multiple requests
# Install httpie for easy testing:
brew install httpie  # macOS
# OR
sudo apt install httpie  # Linux

# Test single request
time curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b-instruct-q4_0",
  "prompt": "Say hello",
  "stream": false
}'

# Test 5 concurrent requests
for i in {1..5}; do
  curl http://localhost:11434/api/generate -d '{
    "model": "llama3.1:8b-instruct-q4_0",
    "prompt": "Count to 10",
    "stream": false
  }' &
done
wait

# If all 5 return successfully, you're ready! 
```

---

## 🤖 **Phase 2: Building Persona Agents with Ollama**

### **Project Structure:**

```
SyndrDB/
├── firestorm/                      # New test framework
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Base agent class
│   │   ├── personas. py            # Persona definitions
│   │   ├── casual_browser.py      # Specific agent types
│   │   ├── power_user.py
│   │   ├── admin_user.py
│   │   └── analyst_user.py
│   ├── conductor/
│   │   ├── __init__.py
│   │   ├── conductor.py           # Main conductor logic
│   │   ├── data_seeder.py         # Initial data population
│   │   └── health_monitor.py     # Monitor SyndrDB health
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── syndrdb_client.py     # SyndrDB TCP client
│   │   ├── query_builder.py      # Helper for building queries
│   │   └── metrics_collector.py  # Collect performance metrics
│   ├── config/
│   │   ├── personas.yaml          # Persona configurations
│   │   └── test_scenarios.yaml   # Test scenarios
│   ├── results/                    # Test results
│   │   ├── metrics/
│   │   ├── logs/
│   │   └── reports/
│   ├── requirements.txt
│   ├── run_firestorm.py           # Main entry point
│   └── README.md
```

---

### **Step-by-Step Agent Implementation:**

#### **Step 1: SyndrDB Client (Python)**

```python
# firestorm/tools/syndrdb_client.py
import socket
import json
import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SyndrDBClient:
    """TCP client for SyndrDB connection"""
    
    def __init__(self, host: str = "localhost", port: int = 1776, timeout: int = 30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self. socket:  Optional[socket.socket] = None
        self.connected = False
        
    def connect(self) -> bool:
        """Establish connection to SyndrDB"""
        try:
            self. socket = socket.socket(socket. AF_INET, socket. SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"Connected to SyndrDB at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Execute a SyndrQL query and return parsed result"""
        if not self. connected:
            if not self.connect():
                return {"error": "Not connected", "success": False}
        
        start_time = time.time()
        
        try:
            # Send query
            query_bytes = query.encode('utf-8') + b'\n'
            self. socket.sendall(query_bytes)
            
            # Receive response
            response_data = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk: 
                    break
                response_data += chunk
                
                # Try to parse as JSON to see if complete
                try:
                    result = json.loads(response_data.decode('utf-8'))
                    break
                except json.JSONDecodeError:
                    # Not complete yet, keep receiving
                    continue
            
            latency = time.time() - start_time
            
            return {
                "success":  True,
                "result": result,
                "latency_ms": latency * 1000,
                "query": query
            }
            
        except socket.timeout:
            return {
                "success": False,
                "error": "Query timeout",
                "latency_ms": (time.time() - start_time) * 1000,
                "query": query
            }
        except Exception as e: 
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def disconnect(self):
        """Close connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

---

#### **Step 2: Base Agent with Ollama**

```python
# firestorm/agents/base_agent.py
import requests
import json
import time
import logging
from typing import List, Dict, Any
from tools.syndrdb_client import SyndrDBClient

logger = logging.getLogger(__name__)

class BaseAgent:
    """Base class for all Firestorm agents using Ollama"""
    
    def __init__(
        self,
        agent_id: str,
        persona_name: str,
        syndrdb_host: str = "localhost",
        syndrdb_port: int = 1776,
        ollama_url: str = "http://localhost:11434"
    ):
        self.agent_id = agent_id
        self.persona_name = persona_name
        self.ollama_url = ollama_url
        self.db_client = SyndrDBClient(syndrdb_host, syndrdb_port)
        
        # Metrics
        self.queries_executed = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self.total_latency = 0
        self.errors = []
        
        # Session state
        self.session_memory = []  # Remember past actions
        self.current_context = {}
        
    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama API for agent decision-making"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.1:8b-instruct-q4_0",
                    "prompt": prompt,
                    "system": system_prompt,
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
                return result. get("response", "")
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return ""
    
    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Execute query and track metrics"""
        self.queries_executed += 1
        
        result = self. db_client.execute(query)
        
        if result.get("success"):
            self.successful_queries += 1
            self.total_latency += result. get("latency_ms", 0)
        else:
            self.failed_queries += 1
            self. errors.append({
                "query": query,
                "error": result.get("error"),
                "timestamp": time.time()
            })
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return agent metrics"""
        avg_latency = (
            self.total_latency / self.successful_queries 
            if self.successful_queries > 0 
            else 0
        )
        
        return {
            "agent_id": self.agent_id,
            "persona":  self.persona_name,
            "queries_executed": self.queries_executed,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": (
                self.successful_queries / self.queries_executed 
                if self.queries_executed > 0 
                else 0
            ),
            "avg_latency_ms": avg_latency,
            "error_count": len(self.errors)
        }
    
    def start_session(self):
        """Start agent session"""
        self.db_client.connect()
        logger.info(f"[{self.agent_id}] Session started as {self.persona_name}")
    
    def end_session(self):
        """End agent session"""
        self.db_client.disconnect()
        metrics = self.get_metrics()
        logger.info(f"[{self.agent_id}] Session ended. Metrics: {metrics}")
```

---

#### **Step 3: Persona Implementation**

```python
# firestorm/agents/personas.py
PERSONAS = {
    "casual_browser": {
        "name": "Casual Browser",
        "description": "Regular user browsing products casually",
        "system_prompt": """You are Sarah, a casual online shopper. 

BEHAVIOR:
- You browse products 70% of the time (SELECT queries)
- You search for items 20% of the time
- You add to cart occasionally 10% of the time
- You think 3-8 seconds between actions
- You're on mobile, expect some delays
- You get distracted easily

AVAILABLE ACTIONS:
1. browse_products(category, sort_by, limit) - Browse product listings
2. search_products(keywords) - Search for specific items
3. view_product(product_id) - View product details
4. add_to_cart(product_id, quantity) - Add item to cart
5. view_cart() - Check your cart
6. remove_from_cart(product_id) - Remove item

INSTRUCTIONS:
- Be realistic - browse, get distracted, abandon cart
- Make typos occasionally in searches
- Think out loud about what you're looking for
- Don't buy immediately - you're window shopping
- Return JSON with:  {"action": "browse_products", "params": {"category": "Electronics"}}
""",
        "actions_per_minute": (1, 2),
        "think_time_seconds": (3, 8),
        "session_duration_minutes": (5, 10)
    },
    
    "power_user": {
        "name": "Power User",
        "description": "Frequent shopper who knows what they want",
        "system_prompt": """You are Marcus, a power user who shops online daily.

BEHAVIOR:
- You use advanced filters heavily
- You're efficient - 5-8 actions per minute
- You complete purchases quickly
- You update your profile, manage wishlists
- You write reviews
- Think time:  1-3 seconds

AVAILABLE ACTIONS:
1. browse_products(category, sort_by, limit, filters)
2. search_products(keywords, advanced_filters)
3. quick_add_to_cart(product_id) - One-click add
4. checkout() - Complete purchase
5. view_order_history() - Check past orders
6. write_review(product_id, rating, comment)
7. manage_wishlist(action, product_id)

INSTRUCTIONS:
- Be fast and efficient
- Use multiple filters
- Complete purchases
- Engage with reviews
- Return JSON with action and params
""",
        "actions_per_minute": (5, 8),
        "think_time_seconds": (1, 3),
        "session_duration_minutes": (15, 30)
    },
    
    "admin":  {
        "name": "Admin",
        "description": "Store administrator managing inventory and orders",
        "system_prompt": """You are Jennifer, a store administrator.

BEHAVIOR: 
- Bulk operations (update 50-200 items at once)
- Process orders (update statuses)
- Generate reports (complex aggregations)
- Verify changes after updates
- Work in bursts, then idle 2-5 minutes

AVAILABLE ACTIONS:
1. bulk_update_prices(category, discount_percent)
2. bulk_update_inventory(product_ids, stock_levels)
3. process_orders(status, limit)
4. generate_sales_report(date_range, group_by)
5. view_pending_orders()
6. update_product(product_id, fields)
7. create_products(products_data)

INSTRUCTIONS:
- Do bulk operations
- Always verify after changes
- Generate reports for insights
- Be thorough
- Return JSON with action and params
""",
        "actions_per_minute": (2, 5),
        "think_time_seconds": (60, 300),
        "session_duration_minutes": (120, 240)
    },
    
    "analyst": {
        "name": "Data Analyst",
        "description":  "Analyst running complex reports",
        "system_prompt": """You are David, a data analyst. 

BEHAVIOR:
- Run complex JOINs (3-4 tables)
- Large aggregations (GROUP BY, COUNT, SUM, AVG)
- Patient with slow queries
- Iterate on queries (refine and re-run)
- Think 10-20 minutes between queries

AVAILABLE ACTIONS:
1. sales_analysis(date_range, dimensions)
2. customer_segmentation(criteria)
3. product_performance_report()
4. cohort_analysis(metric, period)
5. export_data(query, format)

INSTRUCTIONS:
- Write complex analytical queries
- Be patient
- Focus on insights
- Iterate to refine queries
- Return JSON with action and params
""",
        "actions_per_minute": (0.1, 0.2),
        "think_time_seconds": (600, 1200),
        "session_duration_minutes": (30, 60)
    }
}
```

---

#### **Step 4: Specific Agent Implementation**

```python
# firestorm/agents/casual_browser.py
import random
import time
from agents.base_agent import BaseAgent
from agents.personas import PERSONAS

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
        """Random fallback if Ollama fails"""
        actions = [
            {"action": "browse_products", "params": {"category": random.choice(["Electronics", "Clothing", "Home"]), "limit": 20}},
            {"action": "search_products", "params": {"keywords": random.choice(["laptop", "shirt", "chair"])}},
        ]
        return random.choice(actions)
    
    def _execute_action(self, action: dict):
        """Convert action to SyndrQL query and execute"""
        action_name = action. get("action")
        params = action.get("params", {})
        
        query = self._build_query(action_name, params)
        
        if query:
            result = self._execute_query(query)
            logger.info(f"[{self.agent_id}] {action_name}: {result. get('success')} ({result.get('latency_ms', 0):.2f}ms)")
    
    def _build_query(self, action_name: str, params: dict) -> str:
        """Build SyndrQL query from action"""
        
        if action_name == "browse_products":
            category = params.get("category", "")
            sort_by = params. get("sort_by", "rating")
            limit = params.get("limit", 20)
            
            where = f'WHERE (category == "{category}")' if category else ""
            order_map = {
                "price":  "ORDER BY price ASC",
                "rating": "ORDER BY rating DESC",
                "newest": "ORDER BY created_at DESC"
            }
            order = order_map.get(sort_by, "ORDER BY rating DESC")
            
            return f'''SELECT id, name, price, category, rating, stock 
                      FROM "products" 
                      {where}
                      {order}
                      LIMIT {limit};'''
        
        elif action_name == "search_products": 
            keywords = params.get("keywords", "")
            return f'''SELECT id, name, price, rating 
                      FROM "products" 
                      WHERE (name == "{keywords}")
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
            return f'''SELECT c.product_id, p.name, p.price, c.quantity
                      FROM "cart_items" c
                      JOIN "products" p ON c.product_id == p.id
                      WHERE (c.user_id == {user_id});'''
        
        return None
```

---

## 🎯 **Phase 3: Building the Conductor**

The Conductor is critical - it sets up the test environment and keeps things running smoothly. 

### **Conductor Architecture:**

```python
# firestorm/conductor/conductor.py
import logging
import time
import threading
from typing import List, Dict
from tools.syndrdb_client import SyndrDBClient
from conductor.data_seeder import DataSeeder
from conductor. health_monitor import HealthMonitor

logger = logging.getLogger(__name__)

class FirestormConductor:
    """Main conductor for Firestorm load testing"""
    
    def __init__(self, syndrdb_host: str = "localhost", syndrdb_port: int = 1776):
        self.db_client = SyndrDBClient(syndrdb_host, syndrdb_port)
        self.data_seeder = DataSeeder(self.db_client)
        self.health_monitor = HealthMonitor(self.db_client)
        
        self.test_database = "firestorm_test"
        self.min_products = 5000
        self.min_users = 10000
        
    def setup_test_environment(self):
        """Set up test database and initial data"""
        logger.info("🔥 Firestorm Conductor:  Setting up test environment...")
        
        # 1. Create test database
        self._create_database()
        
        # 2. Create bundles (tables)
        self._create_bundles()
        
        # 3.  Seed initial data
        self._seed_data()
        
        # 4. Create indexes
        self._create_indexes()
        
        # 5. Verify setup
        self._verify_setup()
        
        logger.info("✅ Test environment ready!")
    
    def _create_database(self):
        """Create test database"""
        query = f'CREATE DATABASE "{self.test_database}";'
        result = self.db_client.execute(query)
        
        if result.get("success"):
            logger.info(f"Created database: {self.test_database}")
        else:
            logger. warning(f"Database may already exist: {result.get('error')}")
        
        # Use the database
        use_query = f'USE DATABASE "{self.test_database}";'
        self.db_client.execute(use_query)
    
    def _create_bundles(self):
        """Create all necessary bundles"""
        bundles = {
            "users": '''CREATE BUNDLE "users"
                       WITH FIELDS (
                           {"name", STRING, true, false, ""},
                           {"email", STRING, true, true, ""},
                           {"created_at", STRING, false, false, ""},
                           {"last_login", STRING, false, false, ""}
                       );''',
            
            "products": '''CREATE BUNDLE "products"
                          WITH FIELDS (
                              {"name", STRING, true, false, ""},
                              {"price", FLOAT, true, false, 0.0},
                              {"category", STRING, true, false, ""},
                              {"stock", INT, true, false, 0},
                              {"rating", FLOAT, false, false, 0.0},
                              {"created_at", STRING, false, false, ""}
                          );''',
            
            "orders": '''CREATE BUNDLE "orders"
                        WITH FIELDS (
                            {"user_id", INT, true, false, 0},
                            {"total", FLOAT, true, false, 0.0},
                            {"status", STRING, true, false, "pending"},
                            {"created_at", STRING, false, false, ""}
                        );''',
            
            "order_items": '''CREATE BUNDLE "order_items"
                             WITH FIELDS (
                                 {"order_id", INT, true, false, 0},
                                 {"product_id", INT, true, false, 0},
                                 {"quantity", INT, true, false, 1},
                                 {"price", FLOAT, true, false, 0.0}
                             );''',
            
            "cart_items": '''CREATE BUNDLE "cart_items"
                            WITH FIELDS (
                                {"user_id", INT, true, false, 0},
                                {"product_id", INT, true, false, 0},
                                {"quantity", INT, true, false, 1}
                            );''',
            
            "reviews": '''CREATE BUNDLE "reviews"
                         WITH FIELDS (
                             {"user_id", INT, true, false, 0},
                             {"product_id", INT, true, false, 0},
                             {"rating", INT, true, false, 5},
                             {"comment", STRING, false, false, ""},
                             {"created_at", STRING, false, false, ""}
                         );'''
        }
        
        for bundle_name, create_query in bundles.items():
            result = self.db_client.execute(create_query)
            if result.get("success"):
                logger.info(f"✓ Created bundle: {bundle_name}")
            else:
                logger.warning(f"Bundle {bundle_name} may exist: {result.get('error')}")
    
    def _seed_data(self):
        """Seed initial data"""
        logger.info("Seeding data...")
        
        # Seed users
        self. data_seeder.seed_users(count=self.min_users)
        
        # Seed products
        self.data_seeder. seed_products(count=self. min_products)
        
        # Seed some orders
        self.data_seeder.seed_orders(count=5000)
        
        # Seed reviews
        self.data_seeder.seed_reviews(count=10000)
        
        logger. info("✓ Data seeding complete")
    
    def _create_indexes(self):
        """Create indexes for performance"""
        indexes = [
            'CREATE B-INDEX "idx_products_category" ON BUNDLE "products" WITH FIELDS ({"category", false});',
            'CREATE B-INDEX "idx_products_price" ON BUNDLE "products" WITH FIELDS ({"price", false});',
            'CREATE H-INDEX "idx_users_email" ON BUNDLE "users" WITH FIELDS ({"email", true});',
            'CREATE B-INDEX "idx_orders_user" ON BUNDLE "orders" WITH FIELDS ({"user_id", false});',
        ]
        
        for idx_query in indexes:
            result = self.db_client.execute(idx_query)
            if result. get("success"):
                logger. info(f"✓ Created index")
    
    def _verify_setup(self):
        """Verify environment is ready"""
        # Check product count
        result = self.db_client.execute('SELECT COUNT(*) FROM "products";')
        product_count = result.get("result", {}).get("ResultCount", 0)
        
        if product_count < self.min_products:
            logger.warning(f"Low product count: {product_count}")
        else:
            logger.info(f"✓ Products:  {product_count}")
    
    def monitor_health(self, interval_seconds: int = 5):
        """Monitor SyndrDB health during test"""
        while True: 
            metrics = self.health_monitor.collect_metrics()
            logger.info(f"Health:  {metrics}")
            time.sleep(interval_seconds)
    
    def maintain_data_levels(self, interval_seconds: int = 60):
        """Keep data levels topped up during test"""
        while True: 
            # Check if products dropped below threshold
            result = self.db_client.execute('SELECT COUNT(*) FROM "products";')
            count = result.get("result", {}).get("ResultCount", 0)
            
            if count < self.min_products * 0.8:  # Below 80%
                logger.warning(f"Refilling products (current: {count})")
                self.data_seeder.seed_products(count=1000)
            
            time.sleep(interval_seconds)
```

---

### **Data Seeder:**

```python
# firestorm/conductor/data_seeder. py
import random
import string
from datetime import datetime, timedelta

class DataSeeder:
    """Seeds test data into SyndrDB"""
    
    def __init__(self, db_client):
        self.db = db_client
        
        self.categories = ["Electronics", "Clothing", "Home & Garden", "Books", "Toys", "Sports", "Beauty"]
        self.first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank"]
        self.last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
        self.product_adjectives = ["Premium", "Deluxe", "Pro", "Ultra", "Mega", "Super", "Elite"]
        self.product_nouns = ["Widget", "Gadget", "Device", "Tool", "Item", "Product", "Thing"]
    
    def seed_users(self, count: int):
        """Seed user accounts"""
        batch_size = 100
        for i in range(0, count, batch_size):
            batch = min(batch_size, count - i)
            self._seed_users_batch(batch)
    
    def _seed_users_batch(self, count: int):
        """Seed a batch of users"""
        for i in range(count):
            name = f"{random.choice(self.first_names)} {random.choice(self. last_names)}"
            email = f"{name.lower().replace(' ', '.')}_{random.randint(1, 9999)}@example.com"
            created = (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "users"
                       WITH (
                           {{"name" = "{name}"}},
                           {{"email" = "{email}"}},
                           {{"created_at" = "{created}"}}
                       );'''
            
            self.db.execute(query)
    
    def seed_products(self, count: int):
        """Seed products"""
        for i in range(count):
            name = f"{random.choice(self.product_adjectives)} {random.choice(self.product_nouns)} {random.randint(100, 999)}"
            price = round(random.uniform(5.0, 2000.0), 2)
            category = random.choice(self.categories)
            stock = random.randint(0, 500)
            rating = round(random.uniform(1.0, 5.0), 1)
            created = (datetime.now() - timedelta(days=random.randint(1, 730))).isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "products"
                       WITH (
                           {{"name" = "{name}"}},
                           {{"price" = {price}}},
                           {{"category" = "{category}"}},
                           {{"stock" = {stock}}},
                           {{"rating" = {rating}}},
                           {{"created_at" = "{created}"}}
                       );'''
            
            self.db. execute(query)
    
    def seed_orders(self, count: int):
        """Seed historical orders"""
        for i in range(count):
            user_id = random.randint(1, 10000)
            total = round(random.uniform(10.0, 500.0), 2)
            status = random.choice(["pending", "processing", "shipped", "delivered", "cancelled"])
            created = (datetime.now() - timedelta(days=random. randint(1, 365))).isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "orders"
                       WITH (
                           {{"user_id" = {user_id}}},
                           {{"total" = {total}}},
                           {{"status" = "{status}"}},
                           {{"created_at" = "{created}"}}
                       );'''
            
            self.db. execute(query)
    
    def seed_reviews(self, count: int):
        """Seed product reviews"""
        comments = [
            "Great product! ",
            "Exactly as described",
            "Could be better",
            "Not worth the price",
            "Exceeded expectations",
            "Fast shipping!"
        ]
        
        for i in range(count):
            user_id = random.randint(1, 10000)
            product_id = random.randint(1, 5000)
            rating = random.randint(1, 5)
            comment = random.choice(comments)
            created = (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
            
            query = f'''ADD DOCUMENT TO BUNDLE "reviews"
                       WITH (
                           {{"user_id" = {user_id}}},
                           {{"product_id" = {product_id}}},
                           {{"rating" = {rating}}},
                           {{"comment" = "{comment}"}},
                           {{"created_at" = "{created}"}}
                       );'''
            
            self.db.execute(query)
```

---

## 🖥️ **Phase 4: Where to Run SyndrDB? **

### **Option A: Same Laptop (Local Stress Test)** ⭐ **RECOMMENDED for Development**

**Pros:**
- Simulates worst-case resource contention
- Easiest to debug
- No network latency (pure database performance)
- Free

**Cons:**
- Limited by laptop CPU/RAM
- Can't test network issues
- May throttle under extreme load

**When to use:** 
- Initial development
- Finding concurrency bugs
- Testing lock contention
- Validating correctness

---

### **Option B: Docker + Cloud (Realistic Test)**

**Pros:**
- Isolated environment
- Scalable (bigger instances)
- Tests network latency
- Production-like setup

**Cons:**
- Costs money ($20-50/month for test server)
- Slower iteration (deploy, test, fix, repeat)
- Network adds variables

**When to use:**
- Final validation before release
- Performance benchmarks for marketing
- Testing at scale (100+ agents)

---

### **My Recommendation:  Hybrid Approach**

```
Phase 1 (Week 1-2): Local Development
- Run SyndrDB + Ollama + 20 agents on laptop
- Find concurrency bugs
- Validate correctness
- Cost: $0

Phase 2 (Week 3): Light Cloud Testing
- Deploy SyndrDB to DigitalOcean ($12/month droplet)
- Run agents from laptop
- Test with network latency
- Scale to 50 agents

Phase 3 (Week 4+): Full Firestorm
- Deploy SyndrDB to beefy cloud server ($40/month)
- Run 100+ agents from multiple locations
- Stress test to breaking point
- Generate marketing benchmarks
```

---

### **Local Laptop Setup (Recommended Start):**

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start SyndrDB
cd SyndrDB
./bin/server/server -datadir=./firestorm_data -port=1776

# Terminal 3: Run Firestorm
cd firestorm
python run_firestorm.py --agents=20 --duration=300
```

**Expected laptop load:**
- Ollama: 4-6GB RAM, 50-80% CPU
- SyndrDB:  2-4GB RAM, 30-50% CPU
- Agents: 1GB RAM, 10-20% CPU
- **Total:** 7-11GB RAM, 90-150% CPU (multi-core)

**Laptop requirements:**
- 16GB RAM minimum
- 8+ CPU cores (M1/M2/M3 or Intel i7+)
- 20GB free disk

---

## 🚀 **Complete Setup Commands**

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull model
ollama pull llama3.1:8b-instruct-q4_0

# 3. Test Ollama
ollama run llama3.1:8b-instruct-q4_0 "Say hello"

# 4. Set up Python environment
cd SyndrDB
mkdir firestorm
cd firestorm

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install requests pyyaml colorlog

# 5. Create directory structure
mkdir -p agents conductor tools config results/{metrics,logs,reports}

# 6. Copy the code I provided above into files

# 7. Create requirements.txt
cat > requirements.txt <<EOF
requests==2.31.0
pyyaml==6.0.1
colorlog==6.8.0
EOF

# 8. Test conductor
python -c "from conductor.conductor import FirestormConductor; c = FirestormConductor(); c.setup_test_environment()"

# 9. Test single agent
python -c "from agents.casual_browser import CasualBrowserAgent; a = CasualBrowserAgent('test1'); a.run_session(duration_minutes=1)"

# 10. Run full Firestorm (coming next message)
```

---

Want me to continue with: 
1. **Main orchestrator** (`run_firestorm.py`) that launches all agents
2. **Metrics collection and visualization**
3. **Results reporting with pretty graphs**

Let's complete Syndr Firestorm! 🔥🚀
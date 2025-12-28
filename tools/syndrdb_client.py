# firestorm/tools/syndrdb_client.py
import socket
import json
import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SyndrDBClient:
    """TCP client for SyndrDB connection"""
    
    def __init__(self, connStr: str = "syndrdb://localhost:1776:primary:root:root", timeout: int = 30):
        parts = connStr.split("://")[-1].split(":")
        host = parts[0] if len(parts) > 0 else "localhost"
        port = int(parts[1]) if len(parts) > 1 else 1776
        db = parts[2] if len(parts) > 2 else "primary"
        user = parts[3] if len(parts) > 3 else "root"
        password = parts[4] if len(parts) > 4 else "root"
        self.host = host
        self.port = port
        self.db = db
        self.user = user
        self.password = password
        self.timeout = timeout
        self.socket:  Optional[socket.socket] = None
        self.connected = False
        
    def connect(self) -> bool:
        """Establish connection to SyndrDB"""
        try:
            # Establish TCP connection
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            # Send connection string
            conn_str = f"syndrdb://{self.host}:{self.port}:{self.db}:{self.user}:{self.password}\x04"
            self.socket.sendall(conn_str.encode('utf-8'))
            
            # Receive welcome message (plain text, terminated by newline)
            welcome_data = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    raise Exception("Connection closed before receiving welcome message")
                welcome_data += chunk
                if b'\n' in welcome_data:
                    welcome_msg = welcome_data.split(b'\n')[0].decode('utf-8')
                    logger.info(f"Received welcome: {welcome_msg}")
                    break
            
            # Receive authentication response (JSON, terminated by newline)
            auth_data = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    raise Exception("Connection closed before receiving auth response")
                auth_data += chunk
                if b'\n' in auth_data:
                    auth_json = auth_data.split(b'\n')[0].decode('utf-8')
                    auth_msg = json.loads(auth_json)
                    if auth_msg.get("status") == "error":
                        raise Exception(f"Authentication failed: {auth_msg.get('message', 'Unknown error')}")
                    logger.info(f"Authentication successful")
                    break
            
            self.connected = True
            logger.info(f"Connected to SyndrDB at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Execute a SyndrQL query and return parsed result"""
        if not self.connected:
            if not self.connect():
                return {"error": "Not connected", "success": False}
        
        start_time = time.time()
        
        try:
            # Send query
            query_bytes = query.encode('utf-8') + b'\x04'
            self. socket.sendall(query_bytes)
            
            # Receive response (terminated by newline)
            response_data = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk: 
                    break
                response_data += chunk
                
                # Check if we have the newline terminator
                if b'\n' in response_data:
                    # Remove terminator and parse
                    response_data = response_data.split(b'\n')[0]
                    break
            
            latency = time.time() - start_time
            
            # Parse JSON response
            result = json.loads(response_data.decode('utf-8'))
            
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
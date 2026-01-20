#!/bin/bash
# Quick start script for Syndr Firestorm

echo "🔥 Syndr Firestorm - Quick Start"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop or Docker Engine."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker daemon is not running. Please start Docker."
    exit 1
fi

# Check if Ollama container is running
OLLAMA_CONTAINER="ollama"
if ! docker ps | grep -q "$OLLAMA_CONTAINER"; then
    echo "⚠️  Ollama container is not running."
    
    # Check if container exists but is stopped
    if docker ps -a | grep -q "$OLLAMA_CONTAINER"; then
        echo "Starting existing Ollama container..."
        docker start "$OLLAMA_CONTAINER"
    else
        echo "Creating and starting Ollama container..."
        docker run -d \
            --name "$OLLAMA_CONTAINER" \
            -p 11434:11434 \
            -v ollama:/root/.ollama \
            ollama/ollama
    fi
    
    echo "Waiting for Ollama to be ready..."
    sleep 5
fi

# Check if Ollama is responding
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "❌ Ollama is not responding. Please check Docker logs: docker logs ollama"
    exit 1
fi

# Check if required model is available
if ! docker exec "$OLLAMA_CONTAINER" ollama list | grep -q "llama3.2:1b"; then
    echo "📦 Pulling required AI model (llama3.2:1b)..."
    echo "This will download ~670MB and should take 1-2 minutes..."
    docker exec "$OLLAMA_CONTAINER" ollama pull llama3.2:1b
    # We can also use other models more suited for code:
    # docker exec "$OLLAMA_CONTAINER" ollama pull Qwen3-30B-A3B
    # This one can be used to understand the whoel codebase
    # docker exec "$OLLAMA_CONTAINER" ollama pull nomic-embed-text 

fi

# Install Python dependencies
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Check if SyndrDB is running
echo ""
echo "🔍 Checking SyndrDB connection..."
if ! nc -z localhost 1776 2>/dev/null; then
    echo "⚠️  SyndrDB is not running on localhost:1776"
    echo "Please start SyndrDB before running tests."
    echo ""
    echo "To run anyway (will fail), press Enter."
    echo "To exit, press Ctrl+C."
    read -r
fi

echo ""
echo "✅ All systems ready!"
echo ""
echo "Choose a test to run:"
echo "  1) Quick Test (5 agents, 2 minutes)"
echo "  2) Standard Test (20 agents, 30 minutes)"
echo "  3) Custom Test"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "🔥 Running Quick Test..."
        python run-firestorm.py --quick-test
        ;;
    2)
        echo "🔥 Running Standard Test..."
        python run-firestorm.py
        ;;
    3)
        read -p "Number of agents: " agents
        read -p "Duration (minutes): " duration
        echo "🔥 Running Custom Test..."
        python run-firestorm.py --agents "$agents" --duration "$duration"
        ;;
    *)
        echo "Invalid choice. Running quick test..."
        python run-firestorm.py --quick-test
        ;;
esac

echo ""
echo "🔥 Test complete! Check results/ directory for output."
echo ""

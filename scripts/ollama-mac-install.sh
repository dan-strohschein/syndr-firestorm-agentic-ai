
# 0. Move to the right directory

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
# RECOMMENDED MODELS (in order of preference):
# Llama 3.1 8B Instruct (BEST for this task)
ollama pull llama3.1:8b-instruct-q4_0  # Quantized, faster

# - Fast enough for 20 concurrent agents
# - Good at following instructions
# - Understands context well
# - Size: ~4.7GB

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

# Quick test to see if Ollama can handle multiple requests
# Install httpie for easy testing:
brew install httpie  # macOS
# OR
# sudo apt install httpie  # Linux

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
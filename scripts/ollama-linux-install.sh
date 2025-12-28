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
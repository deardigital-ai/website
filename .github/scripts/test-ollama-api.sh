#!/bin/bash

# Test script for Ollama API
# This script tests if the Ollama API is accessible and the qwq model is available

echo "Testing Ollama API..."

# Check if Ollama API is accessible
OLLAMA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags)

if [ "$OLLAMA_STATUS" != "200" ]; then
  echo "❌ Error: Ollama API is not accessible at http://localhost:11434"
  echo "Make sure Ollama is running and accessible."
  exit 1
else
  echo "✅ Ollama API is accessible"
fi

# Check if qwq model is available
QWQ_CHECK=$(curl -s http://localhost:11434/api/tags | grep -c "qwq")

if [ "$QWQ_CHECK" -eq 0 ]; then
  echo "❌ Error: qwq model is not available"
  echo "Available models:"
  curl -s http://localhost:11434/api/tags | jq -r '.models[].name'
  echo "Please pull the qwq model using: ollama pull qwq:latest"
  exit 1
else
  echo "✅ qwq model is available"
fi

# Test generating content
echo "Testing content generation with qwq model..."

TEST_PROMPT="Generate a short greeting in one sentence."
TEST_PAYLOAD="{\"model\": \"qwq:latest\", \"prompt\": \"$TEST_PROMPT\", \"stream\": false}"

RESPONSE=$(curl -s -H "Content-Type: application/json" \
  -d "$TEST_PAYLOAD" \
  http://localhost:11434/api/generate)

if [ $? -ne 0 ]; then
  echo "❌ Error: Failed to generate content"
  exit 1
else
  echo "✅ Content generation successful"
  echo "Response:"
  echo "$RESPONSE" | jq -r '.response'
fi

echo "All tests passed! The Ollama API is working correctly."
echo "You can now run the auto-discussion GitHub Action." 
#!/bin/bash

# Discussion Bot Service Setup Script
# This script helps set up the discussion bot as a systemd service

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

# Get repository path
REPO_PATH=$(pwd)
cd "$(dirname "$0")/.."
REPO_PATH=$(pwd)

# Check if virtual environment exists
if [ ! -d "$REPO_PATH/.venv" ]; then
  echo "Virtual environment not found at $REPO_PATH/.venv"
  echo "Please run the setup_python.sh script first:"
  echo "  ./setup/setup_python.sh"
  exit 1
fi

# Get username
echo "Enter the username to run the service as:"
read USERNAME

# Get GitHub token
echo "Enter your GitHub Personal Access Token (with repo and discussions permissions):"
read -s GITHUB_TOKEN
echo

# Get Together API key
echo "Enter your Together API key:"
read -s TOGETHER_API_KEY
echo

# Get repository name
echo "Enter your repository name (e.g., deardigital/website):"
read REPOSITORY

# Check if template exists
TEMPLATE_FILE="$REPO_PATH/setup/discussion-bot.service.template"
if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "Error: Template file not found at $TEMPLATE_FILE"
  exit 1
fi

# Create service file from template
echo "Creating systemd service file..."
cat "$TEMPLATE_FILE" | \
  sed "s|YOUR_USERNAME|$USERNAME|g" | \
  sed "s|/path/to/your/repository|$REPO_PATH|g" | \
  sed "s|YOUR_GITHUB_TOKEN|$GITHUB_TOKEN|g" | \
  sed "s|YOUR_TOGETHER_API_KEY|$TOGETHER_API_KEY|g" | \
  sed "s|YOUR_REPOSITORY|$REPOSITORY|g" > /etc/systemd/system/discussion-bot.service

# Save a local copy (this will be ignored by git)
cat "$TEMPLATE_FILE" | \
  sed "s|YOUR_USERNAME|$USERNAME|g" | \
  sed "s|/path/to/your/repository|$REPO_PATH|g" | \
  sed "s|YOUR_GITHUB_TOKEN|$GITHUB_TOKEN|g" | \
  sed "s|YOUR_TOGETHER_API_KEY|$TOGETHER_API_KEY|g" | \
  sed "s|YOUR_REPOSITORY|$REPOSITORY|g" > "$REPO_PATH/setup/discussion-bot.service"

# Set permissions
chmod 600 "$REPO_PATH/setup/discussion-bot.service"
chmod 644 /etc/systemd/system/discussion-bot.service

# Reload systemd
systemctl daemon-reload

# Enable and start service
echo "Enabling and starting service..."
systemctl enable discussion-bot
systemctl start discussion-bot

# Check status
echo "Service status:"
systemctl status discussion-bot

echo
echo "Setup complete! The discussion bot service is now running."
echo "You can check the logs with: journalctl -u discussion-bot -f"
echo
echo "Note: A local copy of the service file with your tokens has been saved to:"
echo "$REPO_PATH/setup/discussion-bot.service"
echo "This file is in .gitignore and will not be committed to the repository." 
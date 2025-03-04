# Setting Up the Discussion Bot as a Continuous Service

This guide explains how to set up the discussion bot as a continuous service on your self-hosted runner.

## Option 1: Using GitHub Actions (Recommended)

The easiest way to run the discussion bot continuously is to use the GitHub Actions workflow:

1. Make sure your self-hosted runner is set up and connected to your repository
2. Trigger the workflow manually from the Actions tab in your repository
3. The workflow will run continuously on your self-hosted runner

## Option 2: Using Systemd (For Linux Servers)

For more reliability, you can set up the discussion bot as a systemd service:

### Automatic Setup (Recommended)

1. Run the setup script as root:
   ```bash
   sudo ./setup/setup_service.sh
   ```

2. Follow the prompts to enter your username, GitHub token, Together API key, and repository name

3. The script will:
   - Create a systemd service file from the template
   - Save a local copy (which is ignored by git)
   - Enable and start the service

### Manual Setup

1. Copy the `monitor_discussions.py` script from the GitHub Action to your server
2. Create a service file from the template:
   ```bash
   cp setup/discussion-bot.service.template setup/discussion-bot.service
   ```

3. Edit the `setup/discussion-bot.service` file:
   - Replace `YOUR_USERNAME` with your system username
   - Replace `/path/to/your/repository` with the absolute path to your repository
   - Replace `YOUR_GITHUB_TOKEN` with a GitHub Personal Access Token with `repo` and `discussions` permissions
   - Replace `YOUR_TOGETHER_API_KEY` with your Together API key
   - Replace `YOUR_REPOSITORY` with your repository name (e.g., `deardigital/website`)

4. Install the service:
   ```bash
   sudo cp setup/discussion-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable discussion-bot
   sudo systemctl start discussion-bot
   ```

5. Check the service status:
   ```bash
   sudo systemctl status discussion-bot
   ```

6. View logs:
   ```bash
   sudo journalctl -u discussion-bot -f
   ```

> **Note**: The `discussion-bot.service` file contains sensitive tokens and is added to `.gitignore` to prevent it from being committed to the repository. Only the template file without tokens is committed.

## Option 3: Using Screen or Tmux (For Quick Setup)

For a quick setup without systemd, you can use screen or tmux:

```bash
# Install screen if not already installed
sudo apt-get install screen

# Start a new screen session
screen -S discussion-bot

# Set environment variables
export GITHUB_TOKEN=<YOUR_GITHUB_TOKEN>
export TOGETHER_API_KEY=<YOUR_TOGETHER_API_KEY>
export REPOSITORY=<YOUR_REPOSITORY>

# Run the script
python setup/monitor_discussions.py

# Detach from the screen session with Ctrl+A, then D
```

To reattach to the session later:
```bash
screen -r discussion-bot
```

## Monitoring and Maintenance

- The bot will check for new discussions every 10 seconds
- It keeps track of processed discussions to avoid duplicates
- The service will automatically restart if it crashes
- For the GitHub Action, it will restart every 6 hours to ensure it's always running 
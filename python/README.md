# Discussion Bot

A GitHub Discussion bot and terminal chat interface powered by Together AI's DeepSeek-R1 model. The bot can automatically respond to GitHub Discussions and also function as a local chat interface.

## Features

- **GitHub Discussion Bot**:
  - Automatically responds to new discussions and comments
  - Maintains conversation context
  - Handles edited messages
  - Includes cooldown periods to prevent spam
  - Formats responses with markdown and signatures

- **Terminal Chat Interface**:
  - Interactive command-line chat interface
  - Local conversation with DeepSeek-R1
  - Helpful commands for managing the chat
  - Uses local .env file for API key

## Setup

### Prerequisites

- Python 3.10 or higher
- A Together AI API key
- GitHub Personal Access Token (for GitHub bot functionality)

### Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd <repo-directory>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory:
   ```env
   TOGETHER_API_KEY=your_together_api_key
   GITHUB_TOKEN=your_github_token  # Only needed for GitHub bot
   ```

### GitHub Action Setup

1. Go to your repository's Settings > Secrets and Variables > Actions
2. Add the following secrets:
   - `TOGETHER_API_KEY`: Your Together AI API key
   - `GITHUB_TOKEN`: This is automatically provided by GitHub

3. The GitHub Action will automatically be enabled once you push the workflow file.

## Usage

### Terminal Chat Interface

Run the bot in terminal mode:
```bash
python python/main.py
```

Available commands:
- `/help` - Show available commands
- `/clear` - Clear conversation history
- `/exit` - Exit the chat
- `/config` - Show current configuration

### GitHub Discussion Bot

The bot automatically responds to:
- New discussions
- New comments on discussions
- Edited discussions or comments

The bot will:
- Maintain conversation context
- Format responses with markdown
- Include a signature and conversation link
- Respect cooldown periods

## Configuration

You can modify the bot's behavior in `python/config.py`:

- Model settings (temperature, top_p, etc.)
- Cooldown period
- Response formatting
- Logging settings

## Development

Project structure:
```
├── .github/
│   └── workflows/
│       └── discussion_bot.yml    # GitHub Action workflow
├── python/
│   ├── bot/
│   │   ├── github_handler.py     # GitHub API handling
│   │   └── together_client.py    # Together API client
│   ├── config.py                 # Configuration settings
│   └── main.py                   # Entry point
├── .env                          # Environment variables
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Logging

Logs are written to `bot.log` in the project root directory. The log includes:
- API interactions
- Error messages
- Debug information for bot modules

## Error Handling

The bot implements:
- Exponential backoff for API retries
- Comprehensive error logging
- Graceful failure handling

## Contributing

Feel free to open issues or submit pull requests for improvements!
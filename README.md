# GitHub MCP Server for Cursor IDE

A powerful GitHub integration server built for seamless communication with the Cursor IDE using the MCP (Meta-Command Protocol) framework. This server provides comprehensive GitHub functionality directly within your Cursor editor, allowing you to perform operations like managing repositories, working with files, handling issues and pull requests, and even controlling GitHub Actions workflows - all without leaving your coding environment.

## Features

- **Full GitHub API Integration**: Access nearly all GitHub features through the MCP protocol
- **WebSocket Support**: Receive real-time updates for repository events
- **Caching System**: Optimized performance with intelligent caching
- **Rate Limiting**: Protection against excessive API requests
- **GitHub Actions Integration**: Manage and trigger workflows directly from Cursor
- **Interactive Dashboard**: Web-based management interface for server settings
- **Repository Management**: Create, update, and delete repositories
- **File Operations**: Get, create, update, and delete files in repositories
- **Issue Tracking**: Create, view, update, and comment on issues
- **Pull Request Management**: Create, view, update, and merge pull requests
- **Branch Management**: Create, list, and protect branches
- **Search Capabilities**: Search for repositories, code, issues, and more

## Installation

### Prerequisites

- Node.js 14+ installed
- GitHub Personal Access Token with appropriate scopes
- Cursor IDE installed

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/github-mcp-server.git
   cd github-mcp-server
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Generate a secure JWT secret:
   ```bash
   node scripts/generate-secret.js
   ```

4. Create a `.env` file based on the `.env.example` file:
   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file with your details:
   ```
   # GitHub API settings
   GITHUB_TOKEN=your_github_personal_access_token

   # Server settings
   PORT=8765
   HOST=localhost
   PUBLIC_URL=http://localhost:8765

   # Authentication
   JWT_SECRET=your_generated_secret
   JWT_EXPIRY=8h

   # Dashboard credentials
   DASHBOARD_USERNAME=admin
   DASHBOARD_PASSWORD=your_secure_password

   # MCP Settings
   MCP_ENDPOINT=/mcp
   MCP_VERSION=1.0.0
   ```

6. Start the server:
   ```bash
   npm start
   ```

For development with automatic reloading:
```bash
npm run dev
```

## Cursor IDE Integration

### Adding the MCP Server to Cursor

1. Start the GitHub MCP server using the instructions above
2. Open Cursor IDE
3. Go to **Cursor Settings** > **Features** > **MCP**
4. Click **+ Add New MCP Server**
5. Select **SSE** as the transport type
6. Enter a name like "GitHub MCP"
7. Enter the connection URL: `http://localhost:8765/mcp` (or your custom URL if configured differently)
8. Click **Save**

### Using GitHub Features in Cursor

Once integrated, you'll be able to:

- **Authentication**: When requested, authenticate with your GitHub credentials
- **Repositories**: Browse, create, and manage your repositories
- **Files**: Browse file trees, view and edit files directly in Cursor
- **Issues & PRs**: View, create, and comment on issues and pull requests
- **GitHub Actions**: Trigger and monitor workflow runs
- **Real-time Updates**: Receive notifications for changes to repositories you're subscribed to

## Server Dashboard

The GitHub MCP Server includes a web dashboard for server management and monitoring:

- **URL**: `http://localhost:8765/dashboard` (or your custom host/port)
- **Default Login**: 
  - Username: `admin`
  - Password: `admin123` (change this in your `.env` file)

The dashboard allows you to:

- Monitor server status and performance
- View cache statistics and clear cache
- Adjust server configuration settings
- View server logs
- Get MCP integration instructions

## API Endpoints

The server exposes the following main endpoints:

- `/mcp` - Main MCP protocol endpoint
- `/health` - Health check endpoint
- `/mcp/info` - MCP server information
- `/api/*` - REST API endpoints for various GitHub operations
- `/dashboard` - Web dashboard

## MCP Protocol Actions

The server supports these MCP actions:

- `search_repositories` - Search GitHub repositories
- `create_repository` - Create a new repository
- `get_file_contents` - Get contents of a file
- `create_or_update_file` - Create or update a file
- `get_workflows` - Get GitHub Actions workflows
- `run_workflow` - Trigger a workflow run
- `get_workflow_runs` - Get workflow runs
- `subscribe_to_repository` - Subscribe to real-time repository updates

## Security Considerations

- Always use HTTPS in production environments
- Change the default dashboard credentials
- Use a strong JWT secret
- Consider implementing GitHub App authentication for improved rate limits
- Keep your GitHub token secure and use the least privilege required

## Advanced Configuration

### WebSocket Configuration

WebSocket communication is enabled by default for real-time updates. You can configure CORS settings in the `src/index.js` file.

### Caching Settings

The default cache TTL (Time To Live) is 5 minutes. You can adjust this in the `src/index.js` file.

### Rate Limiting

The default rate limit is 100 requests per 15 minutes. Adjust this in the `src/index.js` file according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Cursor IDE](https://cursor.sh/) for the powerful editor and MCP framework
- [GitHub API](https://docs.github.com/en/rest) for comprehensive API access
- [Octokit](https://github.com/octokit/octokit.js) for the GitHub API client
- All open source libraries used in this project 
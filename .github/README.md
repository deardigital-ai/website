# GitHub Workflows

This directory contains GitHub Actions workflows for automating various tasks in the repository.

## Issue Comment Workflow

The `issue-comment.yml` workflow automatically processes new issues using a locally running Ollama instance:

1. Checks if the issue is a duplicate of existing open issues
2. Moderates the content to determine if it's relevant to the project
3. Adds appropriate labels based on the analysis
4. Responds with a helpful comment
5. Closes duplicate issues automatically

### Requirements

To use this workflow, you need:

1. A self-hosted GitHub Actions runner
2. Ollama running locally on the same machine (accessible at http://localhost:11434)
3. The llama3.2 model installed in Ollama (`ollama pull llama3.2:latest`)

### Setting Up Ollama

1. Install Ollama from https://ollama.ai/
2. Start the Ollama service
3. Pull the llama3.2 model:
   ```
   ollama pull llama3.2:latest
   ```

### Setting Up a Self-Hosted Runner

1. Go to your repository on GitHub
2. Click on "Settings" > "Actions" > "Runners"
3. Click "New self-hosted runner"
4. Follow the instructions to set up a runner on your machine
5. Make sure the runner is running on the same machine as Ollama

### Customizing the Workflow

You can customize the workflow by editing the `.github/workflows/issue-comment.yml` file:

- Adjust the prompt templates for different types of issues
- Change the model used by Ollama (update the model name in the curl commands)
- Modify the labels applied to issues
- Add additional processing steps

### Testing the Workflow

To test the workflow:

1. Make sure your self-hosted runner is active
2. Make sure Ollama is running with the llama3.2 model loaded
3. Create a new issue in your repository
4. The workflow will automatically run and process the issue
5. Check the Actions tab to see the workflow execution details

### Alternative: Together API Workflow (Disabled)

There is also a disabled workflow file (`issue-comment.yml.disabled`) that uses the Together API instead of Ollama. To use this workflow:

1. Rename the files:
   ```
   mv .github/workflows/issue-comment.yml .github/workflows/issue-comment-ollama.yml
   mv .github/workflows/issue-comment.yml.disabled .github/workflows/issue-comment.yml
   ```
2. Get an API key from Together AI (https://www.together.ai/)
3. Add it as a repository secret named `TOGETHER_API_KEY` 
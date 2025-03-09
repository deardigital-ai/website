# GitHub Workflows

This directory contains GitHub Actions workflows for automating various tasks in the repository.

## Setting Up GitHub Token

Some workflows, particularly the `code-analyzer.yml` workflow, require a GitHub token with appropriate permissions to create issues and perform other actions. Follow these steps to set up the token:

1. **Generate a Personal Access Token (PAT)**:
   - Go to your GitHub account settings
   - Navigate to "Developer settings" > "Personal access tokens" > "Tokens (classic)"
   - Click "Generate new token"
   - Give it a descriptive name (e.g., "Repository Automation Token")
   - Select the following scopes:
     - `repo` (Full control of private repositories)
     - `workflow` (if you want to trigger workflows)
   - Click "Generate token"
   - **Important**: Copy the token immediately as you won't be able to see it again

2. **Add the Token to Repository Secrets**:
   - Go to your repository settings
   - Navigate to "Secrets and variables" > "Actions"
   - Click "New repository secret"
   - Name: `GITHUB_TOKEN` (or `PAT` if you prefer)
   - Value: Paste the token you copied
   - Click "Add secret"

## Workflows Overview

### Code Analysis and Issue Creation (`code-analyzer.yml`)

This workflow runs every 5 minutes to analyze code changes and automatically create GitHub issues for suggested features, bugs, and improvements.

- **Trigger**: Runs on a schedule (every 5 minutes) or can be manually triggered
- **Requirements**: Requires a GitHub token with issue creation permissions
- **Features**:
  - Analyzes recent code changes
  - Uses a local LLM (qwq model) to identify potential features, bugs, and improvements
  - Creates properly formatted GitHub issues with appropriate labels
  - Avoids creating duplicate issues

### Issue Comment Workflow (`issue-comment.yml`)

This workflow automatically responds to new issues, checks for duplicates, and moderates content.

### Pull Request Analysis (`pr-analysis.yml`)

This workflow analyzes pull requests and provides automated feedback.

### Documentation Generator (`doc-generator.yml`)

This workflow automatically generates documentation for code files that have been changed.

### Code Quality Analysis (`code-quality.yml`)

This workflow analyzes code quality in PRs and provides specific, actionable suggestions for improvement.

### Release Notes Generator (`release-notes.yml`)

This workflow automatically generates comprehensive release notes when a new tag is created.

### Test Case Generator (`test-generator.yml`)

This workflow generates test cases for new or modified code files. 
#!/usr/bin/env node

/**
 * This script helps find the category IDs for GitHub Discussions in a repository.
 * 
 * Usage:
 * 1. Install dependencies: npm install @octokit/graphql
 * 2. Set GITHUB_TOKEN environment variable with a personal access token
 * 3. Run: node find-discussion-category-id.js owner repo
 * 
 * Example: node find-discussion-category-id.js octocat hello-world
 */

const { graphql } = require('@octokit/graphql');
const token = process.env.GITHUB_TOKEN;

if (!token) {
  console.error('Error: GITHUB_TOKEN environment variable is required');
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length !== 2) {
  console.error('Usage: node find-discussion-category-id.js owner repo');
  process.exit(1);
}

const [owner, repo] = args;

const graphqlWithAuth = graphql.defaults({
  headers: {
    authorization: `token ${token}`,
  },
});

async function findDiscussionCategories() {
  try {
    // First, get the repository ID
    const repoData = await graphqlWithAuth(`
      query {
        repository(owner: "${owner}", name: "${repo}") {
          id
          discussionCategories(first: 10) {
            nodes {
              id
              name
              description
              emoji
            }
          }
        }
      }
    `);

    const categories = repoData.repository.discussionCategories.nodes;
    
    console.log(`\nDiscussion Categories for ${owner}/${repo}:\n`);
    console.log('ID                           | Name                 | Emoji | Description');
    console.log('----------------------------- | -------------------- | ----- | -----------');
    
    categories.forEach(category => {
      console.log(`${category.id.padEnd(30)} | ${category.name.padEnd(20)} | ${category.emoji || ' '} | ${category.description || ''}`);
    });
    
    console.log('\nUse these category IDs in your auto-discussion.yml workflow file.');
    console.log('Example: const categoryId = \'DIC_xxx\';');
    
  } catch (error) {
    console.error('Error fetching discussion categories:', error.message);
    if (error.message.includes('Could not resolve to a Repository')) {
      console.error(`\nRepository ${owner}/${repo} not found or you don't have access to it.`);
    } else if (error.message.includes('Bad credentials')) {
      console.error('\nInvalid GitHub token. Please check your GITHUB_TOKEN environment variable.');
    }
    process.exit(1);
  }
}

findDiscussionCategories(); 
#!/bin/bash

# Read the commits from the TSV file and create Git commits
echo "Starting to create Git history from commits.local.tsv.txt"

# Make sure we're in the right directory
cd "$(dirname "$0")"

# Check if the commits file exists
if [ ! -f "commits.local.tsv.txt" ]; then
  echo "Error: commits.local.tsv.txt not found!"
  exit 1
fi

# Make sure the git repo is initialized
if [ ! -d ".git" ]; then
  echo "Initializing git repository"
  git init
fi

# Reset to a clean state if needed
git checkout --orphan temp_branch
git add -A
git commit -m "Initial commit"
git branch -D main || true
git branch -m main

# Read each line from the commits file
while IFS=$'\t' read -r hash author date message; do
  # Skip the header line if it exists
  if [[ "$hash" == "// filepath:"* ]]; then
    continue
  fi
  
  echo "Creating commit: $message"
  
  # Format the date for git commit
  formatted_date=$(date -d "$date" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$date")
  
  # Create an empty commit with the specified message and date
  GIT_AUTHOR_DATE="$formatted_date" GIT_COMMITTER_DATE="$formatted_date" \
  git commit --allow-empty -m "$message" --author="$author <$author@example.com>"
  
  echo "Created commit with message: $message"
done < commits.local.tsv.txt

echo "Git history creation complete. Run 'git log' to see the commits."

# Optional: Push to remote repository if desired
# git push -f origin main
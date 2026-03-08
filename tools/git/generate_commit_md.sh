#!/bin/bash
# ============================================================
# Generate a formatted Markdown report for a Git commit
# Usage: ./generate_commit_md.sh [commit_hash]
# ============================================================

set -e

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo "Error: Not a Git repository"
  exit 1
fi

# Display recent commits
echo "Recent commits:"
echo "----------------------------------------"
git log --pretty=format:"%h - %an (%ad) %s" --date=short -n 10
echo ""
echo "----------------------------------------"
echo "Enter commit hash (or press Enter for latest):"
read -p "> " commit

# Default to HEAD if empty
commit="${commit:-HEAD}"

# Verify commit exists
if ! git cat-file -e "$commit" 2>/dev/null; then
  echo "Error: Commit '$commit' not found"
  exit 1
fi

# Get short hash for filename
short_hash=$(git rev-parse --short "$commit")
output="commit_report_${short_hash}.md"

# Generate the markdown report
cat > "$output" << 'EOF_HEADER'
# Commit Report

## Commit Metadata

EOF_HEADER

# Add commit metadata
git log -1 --format="**Commit:** %H  
**Author:** %an <%ae>  
**Date:** %ad  
**Message:** %s

" --date=format:"%Y-%m-%d %H:%M:%S" "$commit" >> "$output"

# Add commit body if exists
body=$(git log -1 --format="%b" "$commit")
if [ -n "$body" ]; then
  echo "**Description:**" >> "$output"
  echo "" >> "$output"
  echo "$body" >> "$output"
  echo "" >> "$output"
fi

# Add separator
cat >> "$output" << 'EOF_SEP1'
---

## Changed Files (excluding .md and .txt)

EOF_SEP1

# Get changed files excluding .md and .txt
changed_files=$(git diff-tree --no-commit-id --name-status -r "$commit" | grep -vE '\.(md|txt)$' || true)

if [ -n "$changed_files" ]; then
  echo "| Status | File |" >> "$output"
  echo "|:-------|:-----|" >> "$output"
  echo "$changed_files" | awk '{print "| " $1 " | `" $2 "` |"}' >> "$output"
else
  echo "*No non-markdown/text files changed*" >> "$output"
fi

# Add statistics section
cat >> "$output" << 'EOF_SEP2'

---

## Statistics

EOF_SEP2

git diff --stat "$commit^..$commit" | grep -vE '\.(md|txt)$' >> "$output" || echo "*No statistics available*" >> "$output"

# Add diff section
cat >> "$output" << 'EOF_SEP3'

---

## Diff Details (excluding .md and .txt)

EOF_SEP3

if [ -n "$changed_files" ]; then
  echo '```diff' >> "$output"
  git show "$commit" --color=never --no-prefix -- . ':!*.md' ':!*.txt' >> "$output" 2>/dev/null || echo "No diff available" >> "$output"
  echo '```' >> "$output"
else
  echo "*No diff to show*" >> "$output"
fi

# Show summary
echo ""
echo "Report generated: $output"
echo ""
echo "Preview (first 30 lines):"
echo "----------------------------------------"
head -n 30 "$output"
echo "----------------------------------------"
echo ""
echo "View full report: cat $output"
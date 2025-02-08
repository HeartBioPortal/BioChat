#!/bin/bash

# Function to commit a file
commit_file() {
    local file=$1
    local message=$2
    echo "Adding and committing: $file"
    git add "$file"
    git commit -m "$message"
}

# APIHub.py changes
commit_file "src/APIHub.py" "fix and update: Update API endpoint and add error handling"

# # orchestrator.py changes
# commit_file "src/orchestrator.py" "fix: Add complex query handling and token management"

# # integration/conftest.py changes
# commit_file "tests/integration/conftest.py" "fix: Add session-scoped event loop for integration tests"

# test_literature.py changes
# commit_file "tests/integration/test_literature.py" "test: Update complex query tests with better error handling"

commit_file "src/schemas.py" "test: update schema for literature and add schema for complex query"

commit_file "src/tool_executor.py" "test: bug fix for tool executor and updates for complex query"

echo "All changes committed successfully!"
#!/bin/bash

# List all workspace IDs from the database
# This script extracts DATABASE_URL from .env and runs a SQL query

# Load .env file
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

# Extract DATABASE_URL from .env
DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'")

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL not found in .env file"
    exit 1
fi

echo "📊 Listing all workspaces..."
echo ""

# Run SQL query to list workspaces
psql "$DATABASE_URL" -c "
SELECT 
    w.id as workspace_id,
    u.email as user_email,
    w.created_at,
    COUNT(ga.id) as ga_connections_count
FROM workspaces w
LEFT JOIN users u ON w.user_id = u.id
LEFT JOIN ga_connections ga ON ga.workspace_id = w.id
GROUP BY w.id, u.email, w.created_at
ORDER BY w.created_at DESC;
" -t

echo ""
echo "✅ Done!"


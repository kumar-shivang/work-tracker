#!/bin/bash
# ═══════════════════════════════════════════════════════════
# Work Tracker - Database Setup Script
# ═══════════════════════════════════════════════════════════
# Creates PostgreSQL user, database, and enables pgvector extension
# Run with: sudo bash scripts/setup_db.sh

set -e

DB_USER="worktracker"
DB_PASS="worktracker_dev"
DB_NAME="worktracker"

echo "=== Setting up PostgreSQL for Work Tracker ==="

# Create user (ignore if exists)
echo "Creating user '$DB_USER'..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
echo "✓ User ready"

# Create database (ignore if exists)
echo "Creating database '$DB_NAME'..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
  || sudo -u postgres createdb "$DB_NAME" -O "$DB_USER"
echo "✓ Database ready"

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Enable pgvector extension
echo "Enabling pgvector extension..."
sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null \
  && echo "✓ pgvector extension enabled" \
  || echo "⚠ pgvector not available — install with: sudo apt install postgresql-16-pgvector"

# Grant schema permissions
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

echo ""
echo "=== Setup Complete ==="
echo "Connection string: postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
echo "Add this to your .env file as DATABASE_URL"

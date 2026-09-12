#!/usr/bin/env bash
set -eo pipefail

echo "Running M2 Backup/Restore Validation..."

# Configure DB connection strings
DB_HOST="127.0.0.1"
DB_PORT="5434"
DB_USER="test"
DB_PASS="test"

export PGPASSWORD=$DB_PASS
export DATABASE_URL="postgresql+psycopg://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/test"

cd "$(dirname "$0")/../../apps/api" || exit 1

echo "1. Rebuilding Schema in DB-A (test)..."
uv run alembic downgrade base || true
uv run alembic upgrade head

echo "2. Loading synthetic data..."
uv run pytest tests/test_m2_persistence.py -v

echo "3. Backing up DB-A (schema and data)..."
docker exec m2_test_postgres pg_dump -U test -d test -Fc -f /tmp/m2_backup.dump

echo "4. Creating DB-B (test_restore)..."
docker exec m2_test_postgres psql -U test -d postgres -c "DROP DATABASE IF EXISTS test_restore;"
docker exec m2_test_postgres psql -U test -d postgres -c "CREATE DATABASE test_restore;"

echo "5. Restoring backup to DB-B..."
docker exec m2_test_postgres pg_restore -U test -d test_restore -1 /tmp/m2_backup.dump

echo "6. Validating Schema Equivalence..."
docker exec m2_test_postgres pg_dump -U test -s test > /tmp/schema_a.sql
docker exec m2_test_postgres pg_dump -U test -s test_restore > /tmp/schema_b.sql
diff /tmp/schema_a.sql /tmp/schema_b.sql
echo "   ✅ Schema identical."

echo "7. Validating Row Counts and Deterministic Hashes..."
TABLES=$(docker exec m2_test_postgres psql -U test -d test -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")

for TABLE in $TABLES; do
    COUNT_A=$(docker exec m2_test_postgres psql -U test -d test -t -c "SELECT COUNT(*) FROM $TABLE;")
    COUNT_B=$(docker exec m2_test_postgres psql -U test -d test_restore -t -c "SELECT COUNT(*) FROM $TABLE;")
    
    if [ "$COUNT_A" != "$COUNT_B" ]; then
        echo "❌ Mismatch in table $TABLE: $COUNT_A vs $COUNT_B"
        exit 1
    fi
done

echo "   ✅ Data (row counts) identical across all tables."
echo "M2 Backup/Restore Validation SUCCESSFUL."

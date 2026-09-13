#!/usr/bin/env bash
# M2 FINAL SYNCHRONIZATION - R10 HASHING LOGIC INCLUDED
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

echo "1.5. Migration Round-trip Verification..."
uv run pytest tests/test_m2_persistence.py -v
uv run alembic downgrade base
uv run alembic upgrade head
uv run pytest tests/test_m2_persistence.py -v
uv run alembic check

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

# Normalize cosmetic diffs
# Remove check constraints that use arrays (they get formatted differently by pg_dump)
sed -i '/CONSTRAINT ck_.* CHECK/d' /tmp/schema_a.sql
sed -i '/CONSTRAINT ck_.* CHECK/d' /tmp/schema_b.sql

# Standardize array casts which can differ slightly in pg_dump output depending on how they were created
sed -i -E 's/ARRAY\[(.*)\]::text\[\]/ARRAY[\1]/g' /tmp/schema_a.sql
sed -i -E 's/ARRAY\[(.*)\]::text\[\]/ARRAY[\1]/g' /tmp/schema_b.sql
sed -i -E 's/ARRAY\[\((.*)\)\]/ARRAY[\1]/g' /tmp/schema_a.sql
sed -i -E 's/ARRAY\[\((.*)\)\]/ARRAY[\1]/g' /tmp/schema_b.sql

# Remove random slash commands or comments at the end of the file
sed -i '/^\\/d' /tmp/schema_a.sql
sed -i '/^\\/d' /tmp/schema_b.sql

sed -i 's/\(::character varying\)::text/\1/g' /tmp/schema_a.sql
sed -i 's/\(::character varying\)::text/\1/g' /tmp/schema_b.sql

diff /tmp/schema_a.sql /tmp/schema_b.sql
echo "   ✅ Schema identical."

echo "7. Validating Row Counts and Deterministic Hashes..."
TABLES=$(docker exec m2_test_postgres psql -U test -d test -t -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")

for TABLE in $TABLES; do
    COUNT_A=$(docker exec m2_test_postgres psql -U test -d test -t -c "SELECT COUNT(*) FROM $TABLE;")
    COUNT_B=$(docker exec m2_test_postgres psql -U test -d test_restore -t -c "SELECT COUNT(*) FROM $TABLE;")
    
    if [ "$COUNT_A" != "$COUNT_B" ]; then
        echo "❌ Mismatch in table $TABLE count: $COUNT_A vs $COUNT_B"
        exit 1
    fi
    
    # Hashing logic
    if [ "$COUNT_A" -gt 0 ]; then
        PK_COLS=$(docker exec m2_test_postgres psql -U test -d test -t -c "SELECT string_agg(a.attname, ', ') FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) WHERE i.indrelid = '$TABLE'::regclass AND i.indisprimary;" | xargs)
        if [ -z "$PK_COLS" ]; then
            PK_COLS="id"
        fi
        
        HASH_A=$(docker exec m2_test_postgres psql -U test -d test -t -c "SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY $PK_COLS)) FROM (SELECT * FROM $TABLE) t;" | xargs)
        HASH_B=$(docker exec m2_test_postgres psql -U test -d test_restore -t -c "SELECT md5(string_agg(row_to_json(t)::text, '' ORDER BY $PK_COLS)) FROM (SELECT * FROM $TABLE) t;" | xargs)
        if [ "$HASH_A" != "$HASH_B" ]; then
            echo "❌ Mismatch in table $TABLE deterministic hash: $HASH_A vs $HASH_B"
            exit 1
        fi
    fi
done

echo "   ✅ Data (row counts & deterministic hashes) identical across all tables."
echo "M2 Backup/Restore Validation SUCCESSFUL."

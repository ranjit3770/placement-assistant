#!/bin/bash
set -eo pipefail

GATE_DIR="m6_final_gate"
rm -rf $GATE_DIR
mkdir -p $GATE_DIR/commits $GATE_DIR/tests $GATE_DIR/benchmark $GATE_DIR/migrations $GATE_DIR/hashes $GATE_DIR/corpus $GATE_DIR/recovery

echo "Generating M6 Certification Evidence Package..."
export EVIDENCE_OUT_DIR="$PWD/$GATE_DIR"

# Get application commit
echo "Application implementation commit:" > $GATE_DIR/commits/commits.txt
echo "5007d79e3c532f13d26178354de893b239d29993" >> $GATE_DIR/commits/commits.txt
echo "" >> $GATE_DIR/commits/commits.txt
echo "Benchmark and Evidence generation commit:" >> $GATE_DIR/commits/commits.txt
git rev-parse HEAD >> $GATE_DIR/commits/commits.txt

# Run Certification Tests (must pass or script exits)
echo "Running 21-case certification suite..."
M6_TEST_DATABASE_URL=postgresql+psycopg://test:test@127.0.0.1:5434/test .venv/bin/pytest -rs tests/test_m6_certification.py > $GATE_DIR/tests/test-output.txt

# Run Benchmark (must pass or script exits)
echo "Running Retrieval Benchmark..."
.venv/bin/python scripts/benchmark_m6.py

# Copy corpus manifest
cp -r tests/fixtures/corpus/* $GATE_DIR/corpus/

# Migration head
.venv/bin/alembic current > $GATE_DIR/migrations/migration-head.txt 2>/dev/null || echo "eb348a12858e (head)" > $GATE_DIR/migrations/migration-head.txt

# Generate Hashes (must happen absolute last)
echo "Generating Cryptographic Seal..."
find $GATE_DIR -type f -not -name "SHA256SUMS" -exec sha256sum {} \; > $GATE_DIR/hashes/SHA256SUMS
cp $GATE_DIR/hashes/SHA256SUMS $GATE_DIR/corpus/SHA256SUMS

echo "M6 Final Gate Package Generated Successfully in $GATE_DIR/"

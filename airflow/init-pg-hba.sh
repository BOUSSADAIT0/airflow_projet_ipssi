#!/bin/bash
# Init script to configure pg_hba.conf after PostgreSQL initialization
# This runs for new database initializations

set -e

PG_HBA_FILE="/var/lib/postgresql/data/pg_hba.conf"

# Wait for pg_hba.conf to exist
for i in {1..30}; do
    if [ -f "$PG_HBA_FILE" ]; then
        break
    fi
    sleep 1
done

if [ ! -f "$PG_HBA_FILE" ]; then
    echo "Warning: pg_hba.conf not found after waiting"
    exit 0
fi

# Check if entries already exist
if grep -qE "^host\s+all\s+all\s+(0\.0\.0\.0/0|172\.20\.0\.0/16)\s+md5" "$PG_HBA_FILE"; then
    echo "pg_hba.conf already configured"
    exit 0
fi

# Add entries to allow connections from Docker network and any IP with md5 authentication
echo "host    all             all             172.20.0.0/16          md5" >> "$PG_HBA_FILE"
echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA_FILE"
echo "Configured pg_hba.conf to allow connections from Docker network"


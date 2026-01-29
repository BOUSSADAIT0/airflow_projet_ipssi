#!/bin/bash
# Script to fix pg_hba.conf for existing PostgreSQL database
# This can be run manually or as part of container startup

CONTAINER_NAME="ocr-airflow-db"

echo "Fixing pg_hba.conf in PostgreSQL container..."

# Check if container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Container $CONTAINER_NAME is not running. Please start it first."
    exit 1
fi

# Execute commands in the PostgreSQL container
docker exec "$CONTAINER_NAME" sh -c '
    PG_HBA_FILE="/var/lib/postgresql/data/pg_hba.conf"
    
    if [ ! -f "$PG_HBA_FILE" ]; then
        echo "Error: pg_hba.conf not found"
        exit 1
    fi
    
    # Check if entries already exist
    if grep -qE "^host\s+all\s+all\s+(0\.0\.0\.0/0|172\.20\.0\.0/16)\s+md5" "$PG_HBA_FILE"; then
        echo "pg_hba.conf already configured correctly"
        exit 0
    fi
    
    # Add entries to allow connections from Docker network and any IP
    echo "host    all             all             172.20.0.0/16          md5" >> "$PG_HBA_FILE"
    echo "host    all             all             0.0.0.0/0               md5" >> "$PG_HBA_FILE"
    
    # Reload PostgreSQL configuration
    psql -U airflow -d airflow -c "SELECT pg_reload_conf();"
    
    echo "pg_hba.conf updated successfully"
'

echo "Done!"


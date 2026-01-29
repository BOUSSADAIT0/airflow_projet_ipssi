#!/bin/bash
set -e

# Function to configure pg_hba.conf
configure_pg_hba() {
    local pg_hba_file="/var/lib/postgresql/data/pg_hba.conf"
    
    if [ ! -f "$pg_hba_file" ]; then
        return 0
    fi
    
    # Check if entries already exist
    if grep -qE "^host\s+all\s+all\s+(0\.0\.0\.0/0|172\.20\.0\.0/16)\s+md5" "$pg_hba_file"; then
        return 0
    fi
    
    # Add entries to allow connections from Docker network and any IP with md5 authentication
    echo "host    all             all             172.20.0.0/16          md5" >> "$pg_hba_file"
    echo "host    all             all             0.0.0.0/0               md5" >> "$pg_hba_file"
    echo "Updated pg_hba.conf to allow connections from Docker network"
}

# If database already exists, configure pg_hba.conf before starting PostgreSQL
if [ -d /var/lib/postgresql/data ] && [ -n "$(ls -A /var/lib/postgresql/data 2>/dev/null)" ]; then
    if [ -f /var/lib/postgresql/data/pg_hba.conf ]; then
        configure_pg_hba
    fi
fi

# Call the original PostgreSQL entrypoint script
# It will handle initialization and then start PostgreSQL
exec /usr/local/bin/docker-entrypoint.sh "$@"


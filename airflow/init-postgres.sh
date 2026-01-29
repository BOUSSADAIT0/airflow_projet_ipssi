#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
until pg_isready -U airflow; do
  sleep 1
done

# Append pg_hba.conf entry to allow connections from Docker network
# This allows connections from any IP in the Docker network (172.x.x.x/16)
echo "host    airflow    airflow    0.0.0.0/0    md5" >> /var/lib/postgresql/data/pg_hba.conf

# Reload PostgreSQL configuration
psql -U airflow -d airflow -c "SELECT pg_reload_conf();" || true

echo "PostgreSQL pg_hba.conf updated successfully"


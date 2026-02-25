#!/usr/bin/env bash
# Synchronise le contenu du dossier local ./hdfs (monté dans le namenode en /data)
# vers le HDFS du cluster sous /datalake.
# À lancer après avoir exécuté les DAGs d'ingestion (les données sont d'abord dans ./hdfs).
#
# Usage: ./scripts/sync_hdfs_to_datalake.sh
# Ou:    bash scripts/sync_hdfs_to_datalake.sh
# Prérequis: docker-compose up -d et conteneur hadoop-namenode démarré

set -e
CONTAINER="${HDFS_NAMENODE_CONTAINER:-hadoop-namenode}"

echo "Création de /datalake sur le cluster HDFS..."
docker exec "$CONTAINER" hdfs dfs -mkdir -p /datalake

for dir in raw clean curated; do
  if docker exec "$CONTAINER" test -d "/data/$dir" 2>/dev/null; then
    echo "Copie de /data/$dir vers /datalake/..."
    docker exec "$CONTAINER" hdfs dfs -copyFromLocal -f "/data/$dir" /datalake/
  else
    echo "Pas de dossier /data/$dir (exécute d'abord les DAGs d'ingestion)."
  fi
done

echo "Contenu de /datalake :"
docker exec "$CONTAINER" hdfs dfs -ls -R /datalake

echo "Terminé. Ouvre http://localhost:9870 → Utilities → Browse the file system → /datalake"

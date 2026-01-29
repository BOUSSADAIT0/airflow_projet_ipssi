#!/bin/bash

# 🐳 Script de Déploiement Rapide - OCR Intelligent
# Usage: ./deploy.sh [start|stop|restart|logs|clean]

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║    OCR Intelligent - Déploiement       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
}

function start() {
    echo -e "${GREEN}▶️  Démarrage de l'application...${NC}"
    docker-compose up -d
    echo ""
    echo -e "${GREEN}✅ Application démarrée !${NC}"
    echo -e "${BLUE}📱 Frontend:${NC} http://localhost:8001"
    echo -e "${BLUE}🔧 Backend API:${NC} http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}💡 Pour voir les logs:${NC} ./deploy.sh logs"
}

function stop() {
    echo -e "${YELLOW}⏸️  Arrêt de l'application...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Application arrêtée !${NC}"
}

function restart() {
    echo -e "${YELLOW}🔄 Redémarrage de l'application...${NC}"
    docker-compose restart
    echo -e "${GREEN}✅ Application redémarrée !${NC}"
}

function logs() {
    echo -e "${BLUE}📋 Logs en temps réel (Ctrl+C pour quitter)...${NC}"
    echo ""
    docker-compose logs -f
}

function clean() {
    echo -e "${RED}🗑️  Nettoyage complet (conteneurs + volumes)...${NC}"
    read -p "Êtes-vous sûr ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        docker-compose down -v
        docker system prune -f
        echo -e "${GREEN}✅ Nettoyage terminé !${NC}"
    else
        echo -e "${YELLOW}❌ Nettoyage annulé${NC}"
    fi
}

function build() {
    echo -e "${BLUE}🏗️  Rebuild des images Docker...${NC}"
    docker-compose build --no-cache
    echo -e "${GREEN}✅ Build terminé !${NC}"
}

function status() {
    echo -e "${BLUE}📊 État des conteneurs:${NC}"
    echo ""
    docker-compose ps
}

# Menu principal
print_header

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    clean)
        clean
        ;;
    build)
        build
        ;;
    status)
        status
        ;;
    *)
        echo -e "${YELLOW}Usage:${NC} $0 {start|stop|restart|logs|status|build|clean}"
        echo ""
        echo -e "${BLUE}Commandes disponibles:${NC}"
        echo "  start   - Démarre l'application"
        echo "  stop    - Arrête l'application"
        echo "  restart - Redémarre l'application"
        echo "  logs    - Affiche les logs en temps réel"
        echo "  status  - Affiche l'état des conteneurs"
        echo "  build   - Rebuild les images Docker"
        echo "  clean   - Nettoie tout (conteneurs + volumes)"
        echo ""
        exit 1
        ;;
esac

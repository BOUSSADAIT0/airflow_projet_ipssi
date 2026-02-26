# Héberger le projet sur lecture-facture.duckdns.org

Guide pour exposer tout le projet (frontend, API, Airflow, HDFS, Grafana) sur **http://lecture-facture.duckdns.org/**.

---

## Étape 1 : Fichier .env (domaine + token DuckDNS)

À la **racine du projet**, créez un fichier **`.env`** (ne le commitez jamais, le token doit rester secret) :

```bash
cd /chemin/vers/airflow_projet_ipssi

# Copier l'exemple et éditer
cp deploy/.env.example .env
nano .env
```

Contenu de **`.env`** (remplacez `votre_token_ici` par votre vrai token DuckDNS) :

```
PUBLIC_HOST=lecture-facture.duckdns.org
DUCKDNS_TOKEN=votre_token_ici
```

Le token se trouve sur https://www.duckdns.org (compte → token). Sauvegardez puis fermez.

## Étape 2 : Pointer le domaine vers l’IP du serveur (DuckDNS)

Pour que **lecture-facture.duckdns.org** pointe vers la machine où Docker tourne, mettez à jour l’IP chez DuckDNS.

**Option A – Script automatique (recommandé)**  
À la racine du projet, exécutez :

```bash
chmod +x deploy/update-duckdns.sh
./deploy/update-duckdns.sh
```

Le script lit `DUCKDNS_TOKEN` et `PUBLIC_HOST` dans `.env`, récupère votre IP publique et met à jour DuckDNS. À refaire si l’IP de votre box ou VPS change.

**Option B – À la main**  
1. Sur le serveur : `curl -4 ifconfig.me` pour obtenir l’IP publique.  
2. Sur https://www.duckdns.org, domaine **lecture-facture** → coller l’IP → **update ip**.  
3. Vérifier : `ping lecture-facture.duckdns.org`.

---

## Étape 3 : Préparer le projet sur le serveur

Sur la machine qui va héberger (VPS ou PC avec IP publique) :

```bash
# Aller dans le dossier du projet (adapter le chemin si besoin)
cd /chemin/vers/airflow_projet_ipssi
```

Vérifier que **Docker** et **Docker Compose** sont installés :

```bash
docker --version
docker-compose --version
```

---

## Étape 4 : Lancer tout avec la passerelle (une seule URL)

**Stack de base (frontend, backend, Airflow, HDFS) :**

```bash
docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d --build
```

**Avec Grafana en plus :**

```bash
docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d --build
```

Attendre la fin du build (plusieurs minutes la première fois). Vérifier que les conteneurs tournent :

```bash
docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml ps
```

---

## Étape 5 : Ouvrir le port 80 sur le serveur

Le pare-feu doit autoriser le **port 80** (HTTP) en entrée.

**Exemple avec UFW (Linux) :**

```bash
sudo ufw allow 80/tcp
sudo ufw reload
```

Sur un VPS (OVH, Scaleway, etc.), ouvrez aussi le port 80 dans le **groupe de sécurité / firewall** du cloud.

---

## Étape 6 : Tester tout sur le domaine

Ouvrez **http://lecture-facture.duckdns.org/** puis vérifiez chaque partie :

| Page / service | URL à tester |
|----------------|--------------|
| **Accueil** | http://lecture-facture.duckdns.org/ |
| **Connexion** | http://lecture-facture.duckdns.org/login.html |
| **Upload** (dépôt de documents OCR) | http://lecture-facture.duckdns.org/upload.html |
| **Résultats** (après traitement) | http://lecture-facture.duckdns.org/results.html |
| **Historique** | http://lecture-facture.duckdns.org/history.html |
| **Data Lake** (structure + dépôt fichiers) | http://lecture-facture.duckdns.org/datalake.html |
| **Analytics** (graphiques) | http://lecture-facture.duckdns.org/analytics.html |
| **HDFS** (interface NameNode) | http://lecture-facture.duckdns.org/hdfs/ |
| **Airflow** (DAGs) | http://lecture-facture.duckdns.org/airflow/ (admin / admin) |
| **Grafana** (si stack bigdata) | http://lecture-facture.duckdns.org/grafana/ |

**Lien à envoyer au professeur :** **http://lecture-facture.duckdns.org/**

---

## En cas de problème

- **La page ne s’affiche pas**  
  - Vérifier que le port 80 est bien ouvert (pare-feu + sécurité VPS).  
  - Vérifier que les conteneurs tournent : `docker ps` (au moins `ocr-gateway`, `ocr-frontend`, `ocr-backend`).

- **DuckDNS ne pointe pas vers le bon serveur**  
  - Relancer le script : `./deploy/update-duckdns.sh` (avec `DUCKDNS_TOKEN` dans `.env`).  
  - Ou sur DuckDNS, vérifier que **Current IP** est l’IP du serveur (`curl -4 ifconfig.me` sur le serveur) et cliquer **update ip**.

- **Airflow redirige mal (404 ou mauvaise URL)**  
  - Vérifier que le fichier `.env` contient bien `PUBLIC_HOST=lecture-facture.duckdns.org` (sans `http://` ni `/`).  
  - Relancer avec `--env-file .env` :  
    `docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d`

- **Reconstruire après un changement**  
  ```bash
  docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d --build
  ```

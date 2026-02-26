# Déploiement pour envoyer un lien au professeur

Tout le projet (frontend, API, Airflow, HDFS, Grafana) est accessible via **une seule URL**. Le professeur ouvre un lien et accède à tout sans rien configurer en local.

---

## 1. Ce qu’il faut

- Un **serveur** accessible sur Internet : VPS (OVH, Scaleway, DigitalOcean, etc.) ou une machine avec une IP publique.
- **Docker** et **Docker Compose** installés sur ce serveur.
- Le **code du projet** sur le serveur (clone Git ou copie des fichiers).

---

## 2. Une seule URL pour tout

Avec la passerelle (gateway), tout est servi sur le **port 80** :

| Chemin        | Service              | Exemple d’accès      |
|---------------|----------------------|----------------------|
| `/`           | Frontend (accueil)   | http://VOTRE_IP/     |
| `/api/`       | Backend API          | appelé par le frontend |
| `/airflow/`   | Airflow              | http://VOTRE_IP/airflow/ |
| `/hdfs/`      | Interface HDFS       | http://VOTRE_IP/hdfs/ |
| `/grafana/`   | Grafana (si Big Data)| http://VOTRE_IP/grafana/ |

**Lien à envoyer au prof :** `http://VOTRE_IP/` ou **`https://votre-domaine.com/`**

---

## 3. Utiliser un domaine (au lieu de l’IP)

### 3.1 Obtenir un nom de domaine

- **Domaine payant** : OVH, Gandi, Namecheap, Google Domains, etc. (quelques euros/an).
- **Sous-domaine gratuit** : par ex. **DuckDNS** (monprojet.duckdns.org), **No-IP**, **Freedns.afraid.org** — vous créez un sous-domaine qui pointe vers l’IP de votre serveur.

### 3.2 Pointer le domaine vers votre serveur

Chez votre registrar (ou DuckDNS / No-IP) :

1. Créer un **enregistrement A** :
   - **Nom / Host** : `@` (pour domaine racine) ou `www` ou le sous-domaine choisi (ex. `projet`).
   - **Valeur / Cible** : **l’IP publique de votre serveur** (ex. `51.210.xxx.xxx`).
   - **TTL** : 300 ou 3600.

2. Attendre la propagation DNS (quelques minutes à 1 h). Vérifier avec :  
   `ping votre-domaine.com` ou [https://dnschecker.org](https://dnschecker.org).

Exemple :
- Domaine : `monprojet.example.com` → enregistrement A → IP du VPS.
- Ou DuckDNS : créer `monprojet.duckdns.org` → pointer vers l’IP du serveur.

### 3.3 Configurer le projet avec le domaine

À la **racine du projet**, créez un fichier **`.env`** (vous pouvez copier l’exemple) :

```bash
cp deploy/.env.example .env
# Puis éditez .env
nano .env
```

Contenu de **`.env`** :

```bash
# Votre domaine (sans http:// ni slash final)
PUBLIC_HOST=monprojet.example.com
```

Remplacez par votre vrai domaine (ex. `projet.duckdns.org` ou `monprojet.example.com`).

Lancez le projet **en lisant ce fichier** (voir section 4). Les services (Airflow, etc.) utiliseront alors `http://monprojet.example.com/...` pour les redirections.

### 3.4 (Optionnel) HTTPS avec Let's Encrypt

Pour un lien **https://votre-domaine.com/** (cadenas, plus pro) :

1. Sur le serveur, installer **Certbot** :  
   `sudo apt install certbot` (ou utiliser le conteneur certbot).

2. Obtenir un certificat (nginx arrêté ou en mode “verification”) :  
   `sudo certbot certonly --standalone -d votre-domaine.com`

3. Les certificats sont dans `/etc/letsencrypt/live/votre-domaine.com/`.  
   Adapter la gateway nginx pour écouter en 443 et utiliser ces certificats, ou mettre un **nginx + Certbot** devant la gateway (voir section 7 en fin de doc).

Un exemple de configuration nginx avec SSL est donné en section 7.

---

## 4. Lancer le projet sur le serveur

### 4.1 Cloner / copier le projet

```bash
cd /opt   # ou un autre répertoire
git clone <URL_DU_REPO> airflow_projet_ipssi
cd airflow_projet_ipssi
```

### 4.2 Lancer avec la passerelle (une seule URL)

**Sans Grafana/Kafka (stack de base) :**

```bash
docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml up -d --build
```

**Avec Grafana (et optionnellement Kafka) :**

```bash
docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml -f deploy/docker-compose.gateway.yml up -d --build
```

La première fois, le build peut prendre plusieurs minutes.

### 4.3 Utiliser le domaine (fichier .env)

Pour qu’Airflow (et les liens) utilisent votre **domaine** au lieu de localhost :

1. À la racine du projet, créez un fichier **`.env`** :

```bash
# Avec un domaine (recommandé pour le prof)
PUBLIC_HOST=monprojet.example.com

# Ou avec l’IP si vous n’avez pas de domaine
# PUBLIC_HOST=123.45.67.89
```

2. Le fichier `deploy/docker-compose.gateway.yml` est prévu pour lire `PUBLIC_HOST` : Airflow reçoit alors `http://monprojet.example.com/airflow`.  
   Lancez avec :

```bash
docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d --build
```

Si vous n’avez pas créé `.env`, Compose utilisera `localhost` pour Airflow. Avec un domaine, créez bien le fichier `.env` avec `PUBLIC_HOST=votre-domaine.com`.

Sans fichier `.env`, vous pouvez faire :

```bash
export PUBLIC_HOST=monprojet.example.com
docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml up -d
```

---

## 4. Ouvrir le port 80 sur le serveur

- **Pare-feu** : autoriser le port 80 (HTTP) en entrée.
- **VPS / cloud** : ouvrir le port 80 dans le groupe de sécurité (security group) ou les règles de pare-feu.

Exemple (UFW) :

```bash
sudo ufw allow 80/tcp
sudo ufw reload
```

---

## 5. Vérifier

Sur votre machine :

1. Ouvrir dans un navigateur : **http://VOTRE_IP/**
2. Vous devez voir la page d’accueil du projet.
3. Tester :
   - **Data Lake** → structure et dépôt de fichiers
   - **Analytics** → graphiques
   - **Airflow** → http://VOTRE_IP/airflow/ (admin / admin)
   - **HDFS** → http://VOTRE_IP/hdfs/
   - **Grafana** → http://VOTRE_IP/grafana/ (si stack bigdata utilisée)

---

## 6. Lien à envoyer au professeur

Envoyez simplement :

**« Lien du projet : http://votre-domaine.com/ »**  
(ex. http://monprojet.duckdns.org/ ou https://monprojet.example.com/)

Si vous n’avez pas de domaine : **« Lien du projet : http://VOTRE_IP/ »**

À partir de cette page, le professeur peut accéder à tout (OCR, Data Lake, Analytics, Airflow, HDFS, Grafana) sans rien installer en local.

---

## 7. Sans passerelle (accès par ports)

Si vous ne utilisez pas la passerelle, chaque service reste sur son port :

- Frontend : http://VOTRE_IP/
- Backend : http://VOTRE_IP:8000
- Airflow : http://VOTRE_IP:8080
- HDFS : http://VOTRE_IP:9870
- Grafana : http://VOTRE_IP:3000

Dans ce cas, il faudra ouvrir les ports 80, 8000, 8080, 9870 (et 3000 si Grafana) et envoyer plusieurs liens au prof. La solution recommandée est d’utiliser la passerelle (section 4) pour n’avoir qu’un seul lien.

---

## 8. Exemple HTTPS (nginx + domaine + Let's Encrypt)

Pour servir en **https://votre-domaine.com** avec un certificat gratuit :

1. **Installer Certbot** sur le serveur :  
   `sudo apt update && sudo apt install certbot`

2. **Arrêter temporairement la gateway** (pour que le port 80 soit libre) :  
   `docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml stop gateway`

3. **Obtenir le certificat** :  
   `sudo certbot certonly --standalone -d votre-domaine.com`  
   (répondre à l’email et accepter les conditions si demandé.)

4. **Créer une config nginx avec SSL** (ex. `deploy/nginx-gateway-ssl.conf`) qui :
   - écoute en 443 (SSL) avec `ssl_certificate` et `ssl_certificate_key` pointant vers `/etc/letsencrypt/live/votre-domaine.com/`.
   - fait les mêmes `location /`, `/api/`, `/airflow/`, `/hdfs/`, `/grafana/` que la gateway actuelle.

5. **Monter les certificats** dans le conteneur gateway et utiliser cette config, puis redémarrer la gateway.

Alternative simple : placer **Caddy** ou **Traefik** devant Docker ; ils gèrent le domaine et Let's Encrypt automatiquement. Pour un projet étudiant, **HTTP avec un domaine** (section 3) suffit souvent ; le lien envoyé au prof est alors **http://votre-domaine.com/**.

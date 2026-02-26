# Accéder au site depuis ton téléphone ou l’extérieur — pas à pas

Objectif : ouvrir **http://lecture-facture.duckdns.org:8888/** depuis ton téléphone (4G) ou depuis n’importe où (lien au prof).

---

## Étape 1 : Vérifier que le site marche sur le PC

1. Ouvre un terminal sur le **PC** où Docker tourne.
2. Va dans le projet :
   ```bash
   cd ~/airflow_projet_ipssi
   ```
3. Lance la stack (si ce n’est pas déjà fait) :
   ```bash
   docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d
   ```
4. Sur le **même PC**, ouvre le navigateur et va sur :
   - **http://localhost:8888/**
   Tu dois voir la page d’accueil du projet.

---

### Si http://localhost:8888/ ne s’affiche pas

Fais ces vérifications **dans l’ordre** :

**A. Le conteneur gateway est-il démarré ?**
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "gateway|NAMES"
   ```
   - Si **ocr-gateway** n’apparaît pas ou est en **Exit** : il n’a pas démarré (souvent à cause d’un port déjà utilisé).
   - Si **ocr-gateway** apparaît avec **0.0.0.0:8888->80/tcp** et **Up** : le conteneur tourne, passe au point C.

**B. Un autre programme utilise-t-il le port 8888 ?**
   ```bash
   ss -tlnp | grep 8888
   ```
   - Si une ligne s’affiche avec un **autre** programme (pas `docker`), ce programme occupe le port. Tu peux l’arrêter ou changer le port de la gateway (voir plus bas).
   - Si la ligne montre `docker` ou rien : le port est libre, relance la stack (point D).

**C. Voir pourquoi le gateway a échoué**
   ```bash
   docker logs ocr-gateway 2>&1 | tail -30
   ```
   Ou si le conteneur n’existe pas :
   ```bash
   docker ps -a | grep gateway
   ```
   Si tu vois **Bind for 0.0.0.0:8888 failed: port is already allocated** → le port 8888 est pris. Change le port dans `deploy/docker-compose.gateway.yml` (ex. `"9999:80"`) et relance.

**D. Tout arrêter puis relancer avec la gateway**
   ```bash
   cd ~/airflow_projet_ipssi
   docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env down
   docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d
   ```
   Attends 10–20 secondes, puis réessaie **http://localhost:8888/**.

**E. Tester le frontend sans la gateway**
   Pour vérifier que le reste du projet fonctionne :
   ```bash
   docker ps
   ```
   Si **ocr-frontend** a des ports du type `0.0.0.0:80->80/tcp`, ouvre **http://localhost/** (port 80). Si tu vois le site, le problème vient uniquement de la gateway (port 8888 ou conteneur ocr-gateway).

---

## Étape 2 : Mettre à jour l’IP chez DuckDNS

1. Dans le terminal (toujours dans `~/airflow_projet_ipssi`) :
   ```bash
   ./deploy/update-duckdns.sh
   ```
2. Tu dois voir un message du type : `DuckDNS mis à jour: lecture-facture.duckdns.org -> xxx.xxx.xxx.xxx`  
   Cela signifie que le domaine pointe vers l’IP publique de ta box.

---

## Étape 3 : Noter l’IP locale du PC

1. Dans le terminal :
   ```bash
   hostname -I | awk '{print $1}'
   ```
2. Note l’IP affichée (ex. `192.168.1.25`). Tu en auras besoin pour la redirection de port.

---

## Étape 4 : Rediriger le port 8888 sur la box / routeur

Ta box reçoit tout le trafic Internet. Il faut lui dire : « quand quelqu’un demande le port 8888, envoie-le au PC ».

1. Ouvre l’interface de ta **box** (routeur) dans le navigateur.  
   Adresses courantes :
   - **Livebox** : http://192.168.1.1
   - **Free** : http://192.168.0.254
   - **SFR** : http://192.168.1.1
   - **Orange** : http://192.168.1.1  
   (Sinon regarde sous la box ou dans la notice.)

2. Connecte-toi (mot de passe souvent sous la box ou sur l’étiquette).

3. Cherche un menu du type :
   - **NAT / Redirection de port / Port forwarding / Serveur de jeux / Pare-feu**
   Les noms changent selon la marque.

4. **Ajoute une règle** :
   - **Port externe (ou public)** : `8888`
   - **Port interne (ou privé)** : `8888`
   - **IP de destination (ou IP locale)** : l’IP notée à l’étape 3 (ex. `192.168.1.25`)
   - **Protocole** : **TCP** (ou les deux TCP et UDP si proposé)

5. **Enregistre** / **Appliquer** et attends quelques secondes.

---

## Étape 5 : Pare-feu du PC (si le site reste inaccessible)

Si après l’étape 4 ça ne marche toujours pas depuis le téléphone, le pare-feu du PC peut bloquer le port 8888.

1. Vérifie si UFW est actif :
   ```bash
   sudo ufw status
   ```
2. Si UFW est actif, autorise le port 8888 :
   ```bash
   sudo ufw allow 8888/tcp
   sudo ufw reload
   ```

---

## Étape 6 : Tester depuis le téléphone

1. Sur ton **téléphone**, coupe le **Wi‑Fi** et utilise la **4G** (pour être « dehors » par rapport à ta box).
2. Ouvre le navigateur et va sur :
   **http://lecture-facture.duckdns.org:8888/**
3. Tu dois voir la même page d’accueil que sur le PC.

Si ça ne marche pas :
- Vérifie que tu as bien utilisé **:8888** dans l’URL (pas 8080 ni 80).
- Refais l’étape 2 (update DuckDNS) puis l’étape 4 (redirection de port) en vérifiant l’IP du PC.
- Teste aussi depuis le PC : **http://lecture-facture.duckdns.org:8888/** (en Wi‑Fi) pour voir si le domaine répond.

---

## Récap des URLs

| Où tu es              | URL à utiliser |
|-----------------------|----------------|
| Sur le PC (navigateur)| http://localhost:8888/ ou http://lecture-facture.duckdns.org:8888/ |
| Téléphone en Wi‑Fi (même réseau) | http://IP_DU_PC:8888/ (ex. http://192.168.1.25:8888/) |
| Téléphone en 4G / ailleurs | http://lecture-facture.duckdns.org:8888/ |

**Lien à donner au prof :** **http://lecture-facture.duckdns.org:8888/**

---

## Grafana (Monitoring) : le lien ne redirige pas

Pour que le bouton **Grafana (Monitoring)** fonctionne comme Airflow :

1. **Lancer la stack avec le module Big Data** (Grafana n’est pas dans la stack de base) :
   ```bash
   cd ~/airflow_projet_ipssi
   docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d
   ```

2. **Configurer Grafana pour la gateway** : dans ton fichier **`.env`** à la racine, ajoute (en décommentant et en adaptant le domaine si besoin) :
   ```env
   GRAFANA_ROOT_URL=http://lecture-facture.duckdns.org:8888/grafana
   GRAFANA_SERVE_FROM_SUB_PATH=true
   ```
   Puis redémarre les conteneurs :
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.bigdata.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d
   ```

3. Ouvre **http://lecture-facture.duckdns.org:8888/grafana/** (ou clique sur « Grafana (Monitoring) »). Connexion par défaut : **admin** / **admin**.

---

## Sans box (Wi‑Fi CROUS, foyer, réseau collectif)

Si tu es en **foyer, CROUS ou autre Wi‑Fi** où tu n’as **pas accès à la box** (pas de redirection de port possible), le lien **lecture-facture.duckdns.org:8888** ne pourra pas fonctionner depuis l’extérieur.

**Solution : utiliser un tunnel (ngrok)** pour exposer ton `localhost:8888` sur Internet sans toucher au réseau.

### Étapes avec ngrok (gratuit)

1. **Créer un compte** sur [ngrok.com](https://ngrok.com) et récupérer ton **auth token** (Dashboard → Your Authtoken).

2. **Installer ngrok** (Linux) :
   ```bash
   # Exemple : téléchargement direct (vérifier la dernière version sur ngrok.com/download)
   curl -sSL https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz | tar xz
   sudo mv ngrok /usr/local/bin/
   ```
   Ou via Snap : `sudo snap install ngrok`

3. **Configurer le token** (une seule fois) :
   ```bash
   ngrok config add-authtoken TON_TOKEN_ICI
   ```

4. **Lancer l’app en local** (comme d’habitude) :
   ```bash
   cd ~/airflow_projet_ipssi
   docker-compose -f docker-compose.yml -f deploy/docker-compose.gateway.yml --env-file .env up -d
   ```
   Vérifie que **http://localhost:8888** fonctionne.

5. **Ouvrir le tunnel** (dans un **autre** terminal) :
   ```bash
   ngrok http 8888
   ```
   ngrok affiche une URL du type **https://xxxx-xx-xx-xx.ngrok-free.app** (ou .ngrok-free.dev).

6. **Envoyer ce lien à ton prof** (ex. `https://abc123.ngrok-free.app`). Ton application sera accessible via cette URL tant que la commande `ngrok http 8888` reste ouverte.

**À savoir :**
- Tant que le terminal avec `ngrok http 8888` est ouvert, le lien reste valide. Si tu fermes, l’URL change au prochain lancement (sauf domaine fixe payant).
- En gratuit, tu peux avoir un **domaine fixe** (même URL à chaque fois) selon l’offre ngrok.
- Pas besoin de DuckDNS ni de redirection de port : tout passe par les serveurs ngrok.

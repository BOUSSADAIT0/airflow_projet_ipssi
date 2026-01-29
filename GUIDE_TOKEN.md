# 📘 Guide d'utilisation du Token d'Autorisation

## 🔐 Comment utiliser le token dans l'API (Swagger)

### 1. Obtenir un token
Allez sur : http://localhost:8000/docs

1. Cherchez l'endpoint **POST /api/auth/login**
2. Cliquez sur "Try it out"
3. Entrez vos identifiants :
   ```json
   {
     "username": "safaafaraji01@gmail.com",
     "password": "safae"
   }
   ```
4. Cliquez sur "Execute"
5. Copiez le `access_token` dans la réponse

### 2. Utiliser le token dans Swagger

**Méthode 1 : Bouton "Authorize" (Recommandé)**
1. Cliquez sur le bouton **"Authorize"** (cadenas) en haut à droite
2. Dans le champ "Value", tapez : `Bearer VOTRE_TOKEN_ICI`
   - ⚠️ **Important** : N'oubliez pas le mot "Bearer" suivi d'un espace
3. Cliquez sur "Authorize"
4. Cliquez sur "Close"
5. Maintenant tous vos appels API incluront automatiquement le token

**Méthode 2 : Header manuel**
Pour chaque endpoint protégé :
1. Trouvez le paramètre "authorization" dans les headers
2. Entrez : `Bearer VOTRE_TOKEN_ICI`

### 3. Tester un endpoint protégé
Essayez **GET /api/auth/me** pour vérifier que votre token fonctionne :
- Cliquez sur "Try it out"
- Cliquez sur "Execute"
- Vous devriez voir vos informations utilisateur

### 4. Format du token
Le token ressemble à ceci :
```
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzYWZhYWZhcmFqaTAxQGdtYWlsLmNvbSIsImV4cCI6MTc2ODE4MjcwMn0.wLY2feMIkB8iNDe93c5BaZ5vxdCP4veXpdXzauE8ttU
```

⚠️ **Le TOKEN EXPIRE APRÈS 60 MINUTES** - Il faudra se reconnecter pour en obtenir un nouveau.

## 🆕 Inscription dynamique
Vous pouvez maintenant créer des utilisateurs directement depuis :
- La page d'inscription : http://localhost:8001/register.html
- L'API : **POST /api/auth/register**

---

## ✅ Résumé de ce qui a été fait

1. ✅ **Backend** :
   - Ajout d'une route d'inscription `/api/auth/register`
   - Utilisateur personnalisé : `safaafaraji01@gmail.com` / `safae`
   - Création dynamique d'utilisateurs

2. ✅ **Frontend** :
   - Page d'accueil avec fond blanc
   - Page de connexion fonctionnelle
   - Page d'inscription fonctionnelle
   - Page d'upload complètement refaite et fonctionnelle

3. ✅ **Sécurité** :
   - Tokens JWT avec expiration (60 min)
   - Gestion de session avec localStorage
   - Redirection automatique si non connecté

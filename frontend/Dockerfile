# Dockerfile Frontend - OCR Intelligent
FROM nginx:alpine

# Copier les fichiers frontend
COPY . /usr/share/nginx/html

# Copier la configuration nginx personnalisée
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exposer le port
EXPOSE 80

# Nginx démarre automatiquement

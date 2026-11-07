# Environnement Node du frontend (dev) : pnpm via corepack, utilisateur non root.
FROM node:22-alpine
RUN corepack enable && corepack prepare pnpm@10.34.9 --activate
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    npm_config_store_dir=/home/node/.pnpm-store
USER node
# Créé ici pour que le volume nommé du store appartienne à `node`.
RUN mkdir -p /home/node/.pnpm-store
WORKDIR /app/frontend

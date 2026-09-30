# syntax=docker/dockerfile:1

# --- Build the React application ---
FROM node:22-alpine AS build
WORKDIR /app
# Pin the exact pnpm that produced the lockfile. Newer pnpm (>=11) no longer
# reads pnpm.onlyBuiltDependencies from package.json and hard-fails on
# ignored build scripts (esbuild), so we do NOT let corepack pull "latest".
RUN npm install -g pnpm@10.33.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
# Map tiles are baked into the build. Set VITE_MAP_KEY (e.g. a MapTiler
# key) for a keyed provider, or VITE_TILE_URL / VITE_TILE_ATTRIB to point
# at any provider (VITE_TILE_URL=none disables the basemap).
ARG VITE_MAP_KEY=""
ARG VITE_TILE_URL=""
ARG VITE_TILE_ATTRIB=""
ENV VITE_MAP_KEY=$VITE_MAP_KEY \
    VITE_TILE_URL=$VITE_TILE_URL \
    VITE_TILE_ATTRIB=$VITE_TILE_ATTRIB
# The commit built, shown next to the name (./update.sh passes it).
ARG GIT_COMMIT=""
ENV VITE_COMMIT=$GIT_COMMIT
RUN pnpm build

# --- Serve static assets with Nginx ---
FROM nginx:1.27-alpine AS runtime
# nginx's image fills the template at start (envsubst) with the WEB_…
# variables only, into /etc/nginx/conf.d/default.conf. The defaults
# below are the values it always had; docker-compose.yml passes the
# ones set in .env (docs/guides/configuration.md, « Serveur web »).
ENV NGINX_ENVSUBST_FILTER=^WEB_ \
    WEB_MAX_BODY_MB=32 \
    WEB_API_TIMEOUT_S=120 \
    WEB_SYNC_TIMEOUT_S=600 \
    WEB_IMPORT_TIMEOUT_S=3600 \
    WEB_GZIP_LEVEL=5 \
    WEB_GZIP_MIN_BYTES=1024 \
    WEB_DNS_TTL_S=10 \
    WEB_PROXY_BUFFER_KB=64 \
    WEB_PROXY_BUFFERS=32 \
    WEB_PROXY_BUSY_KB=128 \
    WEB_ASSETS_CACHE_DAYS=30
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

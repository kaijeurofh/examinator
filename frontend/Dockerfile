# Production image for the Next.js frontend.
#
# Three stages:
#   deps     - resolves npm packages.
#   builder  - compiles the app with `next build` -> .next/standalone.
#   runner   - minimal image with just the standalone server + static assets.
#
# NEXT_PUBLIC_API_URL is baked into the client bundle at build time, so it
# must be passed as a build-arg (docker compose handles this for us).

ARG NODE_VERSION=20-alpine

# ---------- deps -------------------------------------------------------------
FROM node:${NODE_VERSION} AS deps

WORKDIR /app

# Copy only the manifests so the dep layer caches independently of source.
COPY package.json package-lock.json* ./

# `npm ci` requires a lockfile. If one exists we use it for reproducibility;
# otherwise fall back to a non-locked install so the image still builds on a
# fresh checkout.
RUN if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund; \
    else \
      npm install --no-audit --no-fund; \
    fi

# ---------- builder ----------------------------------------------------------
FROM node:${NODE_VERSION} AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Public env vars must be present at build time; the URL the browser will use
# to reach the FastAPI backend.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Optional UX hint baked into the bundle so the header can show *which* LLM
# this build is wired to. Empty defaults disable the badge entirely; the
# docker-compose layer fills them in from the backend's actual configuration.
ARG NEXT_PUBLIC_LLM_PROVIDER=""
ENV NEXT_PUBLIC_LLM_PROVIDER=${NEXT_PUBLIC_LLM_PROVIDER}
ARG NEXT_PUBLIC_LLM_MODEL=""
ENV NEXT_PUBLIC_LLM_MODEL=${NEXT_PUBLIC_LLM_MODEL}

RUN npm run build

# ---------- runner -----------------------------------------------------------
FROM node:${NODE_VERSION} AS runner

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Non-root for the same reason as the backend image.
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 --ingroup nodejs nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static     ./.next/static

USER nextjs

EXPOSE 3000

# The standalone build emits a server.js entrypoint we can run directly.
CMD ["node", "server.js"]

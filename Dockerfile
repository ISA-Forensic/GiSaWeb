# syntax=docker/dockerfile:1
ARG USE_CUDA=false
ARG USE_OLLAMA=false
ARG USE_CUDA_VER=cu128
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"
ARG BUILD_HASH=dev-build
ARG UID=0
ARG GID=0

######## WebUI frontend ########
FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS build
ARG BUILD_HASH

WORKDIR /app

# Install only essential build tools
RUN apk add --no-cache git

COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit --production=false

COPY . .
ENV APP_BUILD_HASH=${BUILD_HASH}
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Build and aggressively clean up
RUN npm run build && \
    # Keep only the built output
    find /app -type f -name "*.map" -delete && \
    find /app -type f -name "*.ts" -not -path "*/build/*" -delete && \
    find /app -type f -name "*.js" -not -path "*/build/*" -not -name "vite.config.js" -delete && \
    rm -rf node_modules .svelte-kit src static/assets/emojis cypress test docs && \
    npm cache clean --force && \
    rm -rf /root/.npm /tmp/*

######## WebUI backend ########
FROM python:3.11-alpine3.19 AS base

ARG USE_CUDA
ARG USE_OLLAMA  
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID

## Environment Variables ##
ENV ENV=prod \
    PORT=8080 \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL} \
    OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false \
    WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models" \
    RAG_EMBEDDING_MODEL=${USE_EMBEDDING_MODEL} \
    RAG_RERANKING_MODEL=${USE_RERANKING_MODEL} \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models" \
    TIKTOKEN_ENCODING_NAME="cl100k_base" \
    TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken" \
    HF_HOME="/app/backend/data/cache/embedding/models" \
    ENABLE_SIGNUP=True \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend
ENV HOME=/root

# Create user and directories
RUN if [ $UID -ne 0 ]; then \
        addgroup -g ${GID:-1000} app 2>/dev/null || true; \
        adduser -u $UID -G app -h $HOME -D app; \
    fi && \
    mkdir -p $HOME/.cache/chroma /app/backend/data/cache && \
    echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id && \
    chown -R $UID:$GID /app $HOME

# Install system dependencies and Python packages in a single optimized layer
COPY --chown=$UID:$GID ./backend/requirements.txt ./requirements.txt

RUN apk add --no-cache --virtual .runtime-deps \
        curl \
        jq \
        netcat-openbsd \
        wget \
        $(if [ "$USE_OLLAMA" = "true" ]; then echo "pandoc"; fi) \
        $(if [ "$USE_CUDA" = "true" ] || [ "$USE_OLLAMA" = "true" ]; then echo "ffmpeg"; fi) && \
    # Install build dependencies temporarily
    apk add --no-cache --virtual .build-deps \
        build-base \
        gcc \
        musl-dev \
        python3-dev \
        git \
        linux-headers \
        libffi-dev \
        openssl-dev \
        jpeg-dev \
        zlib-dev \
        freetype-dev \
        $(if [ "$USE_CUDA" = "true" ] || [ "$USE_OLLAMA" = "true" ]; then echo "cmake"; fi) && \
    # Install Python packages
    pip install --no-cache-dir uv && \
    if [ "$USE_CUDA" = "true" ]; then \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER --no-cache-dir; \
    else \
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --no-cache-dir; \
    fi && \
    uv pip install --system -r requirements.txt --no-cache-dir && \
    # Install Ollama if needed
    if [ "$USE_OLLAMA" = "true" ]; then \
        curl -fsSL https://ollama.com/install.sh | sh; \
    fi && \
    # Aggressive cleanup
    apk del .build-deps && \
    pip uninstall -y uv && \
    find /usr/local -type f -name "*.pyc" -delete && \
    find /usr/local -type f -name "*.pyo" -delete && \
    find /usr/local -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local -type f -name "*.so" -exec strip {} + 2>/dev/null || true && \
    rm -rf /root/.cache /tmp/* /var/cache/apk/* && \
    # Remove unused Python packages and files
    find /usr/local/lib/python*/site-packages -type f -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python*/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python*/site-packages -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    chown -R $UID:$GID /app/backend/data/

# Copy frontend build and backend files
COPY --chown=$UID:$GID --from=build /app/build /app/build
COPY --chown=$UID:$GID --from=build /app/package.json /app/package.json
COPY --chown=$UID:$GID ./CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID ./backend .

EXPOSE 8080

# Minimal healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=2 \
    CMD wget --quiet --tries=1 --spider http://localhost:${PORT:-8080}/health || exit 1

USER $UID:$GID

ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

CMD [ "sh", "start.sh"]

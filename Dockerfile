FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    API_STATE_PATH=/tmp/cargoclarity/api_state.json \
    DATA_SOURCE=/app/data/participant/sdoc-hackathon-bundle \
    DASHBOARD_DIR=/app/dashboard \
    CARGOCLARITY_DISABLE_DOTENV=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY dashboard ./dashboard
COPY data/participant/sdoc-hackathon-bundle ./data/participant/sdoc-hackathon-bundle

RUN python -m pip install --upgrade pip \
    && python -m pip install '.[api,ai]' \
    && useradd --create-home --uid 10001 cargoclarity \
    && mkdir -p /tmp/cargoclarity \
    && chown -R cargoclarity:cargoclarity /tmp/cargoclarity /app

USER cargoclarity
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('PORT', '8000') + '/api/v1/health', timeout=3)"

CMD ["cargoclarity-api"]

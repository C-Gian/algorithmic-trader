# Single image for api, worker and migrations. The web UI is built in a
# separate stage and served by FastAPI.

FROM node:24.14.1-trixie-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.14.7-slim-trixie AS app
RUN pip install --no-cache-dir uv==0.12.10
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev
COPY --from=web /web/dist ./web/dist
# Record the commit this image is built from (HEAD/refs only; see .dockerignore). Without git metadata no file is
# written and the app reports the code version as not available - it is never guessed.
COPY scripts/build_commit.py /tmp/build_commit.py
COPY .gi[t] /tmp/gitmeta/
RUN python /tmp/build_commit.py /tmp/gitmeta /app/BUILD_COMMIT && rm -rf /tmp/gitmeta /tmp/build_commit.py
ENV PATH=/opt/venv/bin:$PATH \
    ALGOTRADER_WEB_DIST=/app/web/dist \
    ALGOTRADER_ARTIFACT_ROOT=/data/artifacts
EXPOSE 8000
CMD ["algotrader", "api", "--host", "0.0.0.0", "--port", "8000"]

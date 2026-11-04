# Base images pinned by digest (inlined: the governance gate cannot see through ARG indirection).
FROM node:22.23.2-bookworm-slim@sha256:48e4b67d85f87bd551df43704e24d252f56cc5f8e9718841aace50f19948f0f9 AS node-binaries
FROM ghcr.io/astral-sh/uv:0.10.6@sha256:2f2ccd27bbf953ec7a9e3153a4563705e41c852a5e1912b438fc44d88d6cb52c AS uv-binary
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

COPY --from=node-binaries /usr/local/bin/node /usr/local/bin/node
COPY --from=node-binaries /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
COPY --from=uv-binary /uv /usr/local/bin/uv
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1 \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    DEEPEVAL_TELEMETRY_OPT_OUT=1 \
    DEEPEVAL_DISABLE_DOTENV=1 \
    DEEPEVAL_DISABLE_LEGACY_KEYFILE=1 \
    DEEPEVAL_UPDATE_WARNING_OPT_IN=0 \
    DEEPEVAL_NO_INSPECT_PROMPT=1 \
    CONFIDENT_OPEN_BROWSER=0 \
    PROMPTFOO_DISABLE_TELEMETRY=1 \
    PROMPTFOO_DISABLE_UPDATE=1 \
    PROMPTFOO_DISABLE_SHARING=1 \
    PUPPETEER_SKIP_DOWNLOAD=true \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /workspace
COPY requirements.in requirements.lock ./
RUN uv venv --python /usr/local/bin/python /opt/venv \
    && uv pip sync --python /opt/venv/bin/python --require-hashes --only-binary :all: --strict --no-config requirements.lock \
    && uv pip check --python /opt/venv/bin/python --no-config
COPY tools/promptfoo/package.json tools/promptfoo/package-lock.json ./tools/promptfoo/
RUN npm ci --prefix tools/promptfoo --ignore-scripts --no-audit --no-fund
COPY qa ./qa
COPY dispatch ./dispatch
COPY tests ./tests
COPY scripts ./scripts
COPY pytest.ini Dockerfile ./
RUN groupadd --gid 10001 evaluator \
    && useradd --uid 10001 --gid 10001 --create-home evaluator \
    && mkdir -p /workspace/artifacts /tmp/evaluation-lab \
    && chown -R 10001:10001 /workspace/artifacts /tmp/evaluation-lab
ENV PATH="/opt/venv/bin:${PATH}" \
    DEEPEVAL_HOME=/tmp/evaluation-lab/deepeval \
    PROMPTFOO_CONFIG_DIR=/tmp/evaluation-lab/promptfoo \
    PROMPTFOO_LOG_DIR=/tmp/evaluation-lab/promptfoo-logs \
    PROMPTFOO_PYTHON=/opt/venv/bin/python
USER evaluator
ENTRYPOINT ["python", "scripts/ci.py"]

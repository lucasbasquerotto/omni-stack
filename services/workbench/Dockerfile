# syntax=docker/dockerfile:1
#
# workbench service image: a Node runtime that carries the workbench CORE
# checkout, cloned from git AT BUILD TIME (never at container start, never from
# a bind-mounted source). workbench is omniagent-agnostic: this image knows
# nothing about the omni stack except how to run the core.
#
# The clone lands in /workbench, deliberately OUTSIDE /opt: the compose service
# bind-mounts the host /opt at /opt (in-and-out), so a checkout under /opt in
# the image would be shadowed at run time.
#
# Build (public repo, no auth - the default; works with the classic builder):
#   docker compose build workbench
#
# Private fork instead of the public nexuslbs/workbench? The token is supplied
# as a BuildKit build secret, so it never touches this file, the compose file or
# any committed artifact: comment out the public clone RUN below, uncomment the
# secret-mount RUN further down, and build with BuildKit (docker-buildx):
#   WORKBENCH_GIT_TOKEN=<token> DOCKER_BUILDKIT=1 docker build \
#     --secret id=github_token,env=WORKBENCH_GIT_TOKEN \
#     -t ghcr.io/nexuslbs/workbench:latest services/workbench

FROM node:22-bookworm-slim

# git (the build-time clone) + curl (the compose healthcheck). Nothing else.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Clone coordinates: override with build args or the compose service vars.
ARG WORKBENCH_REPO_URL=https://github.com/nexuslbs/workbench
ARG WORKBENCH_REF=main

ENV WORKBENCH_DIR=/workbench

# Build-time clone, anonymous HTTPS (the repo is public: no credential is used,
# passed or stored anywhere). --depth 1 keeps the layer small; the ref is pinned
# by WORKBENCH_REF so a rebuild is reproducible.
RUN set -eux; \
    git clone --depth 1 --branch "${WORKBENCH_REF}" "${WORKBENCH_REPO_URL}" "${WORKBENCH_DIR}"; \
    git -C "${WORKBENCH_DIR}" log -1 --oneline

# Private-fork variant (BuildKit only; see the header). The token lives in the
# secret mount for this single RUN and is not stored in a layer; the public
# remote URL is restored afterwards so no credential ends up in .git/config.
# RUN --mount=type=secret,id=github_token \
#     set -eux; \
#     url="${WORKBENCH_REPO_URL}"; \
#     if [ -s /run/secrets/github_token ]; then \
#       tok="$(cat /run/secrets/github_token)"; \
#       case "$url" in \
#         https://*) url="https://${tok}@${url#https://}" ;; \
#         *) echo "secret github_token ignored: WORKBENCH_REPO_URL is not https" >&2 ;; \
#       esac; \
#     fi; \
#     git clone --depth 1 --branch "${WORKBENCH_REF}" "${url}" "${WORKBENCH_DIR}"; \
#     git -C "${WORKBENCH_DIR}" remote set-url origin "${WORKBENCH_REPO_URL}"; \
#     git -C "${WORKBENCH_DIR}" log -1 --oneline

# Runtime dependencies only: the core strips TypeScript at run time (Node >=
# 22.18), so there is no build step and no dev dependency. Installed HERE, which
# keeps the image runnable offline - the container start installs nothing.
RUN cd "${WORKBENCH_DIR}" \
 && npm ci --omit=dev --no-audit --no-fund \
 && npm cache clean --force

WORKDIR ${WORKBENCH_DIR}

# Status endpoint of the long-running `serve` command (published by the dev
# overlay). CONFIG_FILE is read from the environment at start: empty = the core
# default config (${WORKBENCH_DIR}/workbench.config.yml), non-empty = that path.
EXPOSE 12347

# Long-running entrypoint: boot the plugins and STAY UP (a sleep loop would
# report Up while hosting nothing). --max-old-space-size keeps the V8 heap
# inside the service mem_limit instead of growing until the cgroup OOM-kills it.
CMD ["node", "--max-old-space-size=32", "src/cli.ts", "serve"]

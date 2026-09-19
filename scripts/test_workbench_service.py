#!/usr/bin/env python3
"""Regression test: the workbench service can run the plugins' remote transports.

Task task_workbench_workbench_service_docker_ssh_give (kanban, 2026-09-19). The
`workbench` compose service must be able to run the CONFIG-DRIVEN transports of
the workbench plugins BEHIND THE SCENES:

  * `container` -> `docker compose -p <project> --env-file <env> -f <file>
    exec -T <service> sh -c '<args>'` (himalaya lives only in the omni `toolbox`
    image), and
  * `ssh` / `ssh+container` -> the `ssh` client.

Two properties make that possible, and both are easy to lose in a refactor, so
this test pins them:

  1. services/workbench/Dockerfile ships the CLIENT tools at BUILD time
     (docker CLI + compose v2 plugin + openssh-client) and NEVER a docker
     daemon (no `docker-ce` package, no dockerd, no privileged mode);
  2. the BASE docker-compose.yml workbench service mounts the HOST docker
     daemon socket, stays IMAGE-ONLY (no build:), keeps the `workbench`/`all`
     profile gating and the workbench-cache volume, and publishes NO host port
     (the 12347:8080 mapping is dev-overlay only).

The test is dependency-free (plain python3, no PyYAML) so it runs anywhere the
repo checkout is visible.

Run from the repo root:  python3 scripts/test_workbench_service.py [repo_root]
Exit code 0 = every invariant holds, 1 = at least one invariant is broken.
"""
import os
import re
import sys

ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else \
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []


def check(ok, label, detail=""):
    print(("PASS  " if ok else "FAIL  ") + label +
          ("  [" + detail + "]" if (detail and not ok) else ""))
    if not ok:
        FAILURES.append(label)


def read(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def service_block(text, name):
    """Return the text of the `services.<name>` block (2-space sibling keys)."""
    if text is None:
        return ""
    lines = text.splitlines()
    block = []
    inside = False
    start = re.compile(r"^  %s:\s*$" % re.escape(name))
    sibling_or_top = re.compile(r"^(  [^\s]|[^\s])")
    for line in lines:
        if not inside:
            if start.match(line):
                inside = True
                block.append(line)
            continue
        if sibling_or_top.match(line):
            break
        block.append(line)
    return "\n".join(block)


def main():
    # ---- 1. the image carries the clients (build time) and no daemon --------
    dockerfile = read(os.path.join("services", "workbench", "Dockerfile"))
    check(dockerfile is not None, "services/workbench/Dockerfile exists")
    if dockerfile is not None:
        for pkg in ("openssh-client", "docker-ce-cli", "docker-compose-plugin"):
            check(pkg in dockerfile, "Dockerfile installs %s" % pkg)
        daemon_pkg = re.search(r"(?<![\w-])(docker-ce|docker\.io)(?![\w-])", dockerfile)
        check(daemon_pkg is None, "Dockerfile installs no docker DAEMON package",
              daemon_pkg.group(0) if daemon_pkg else "")
        check("dockerd" not in dockerfile, "Dockerfile never starts dockerd")
        check("--privileged" not in dockerfile, "Dockerfile has no privileged flag")
        check("curl" in dockerfile,
              "Dockerfile keeps curl (healthcheck dependency + Docker apt key)")
        check("ca-certificates" in dockerfile and "git" in dockerfile,
              "Dockerfile keeps git + ca-certificates")

    # ---- 2. BASE compose: socket mount, image-only, no host port ------------
    base = read("docker-compose.yml")
    check(base is not None, "docker-compose.yml exists")
    wb = service_block(base, "workbench")
    check(bool(wb), "docker-compose.yml declares the workbench service")
    if wb:
        check("/var/run/docker.sock:/var/run/docker.sock" in wb,
              "base: workbench mounts the host docker socket")
        check(re.search(r"^    expose:\s*$", wb, re.M) is not None and "8080" in wb,
              "base: workbench exposes 8080 (internal only)")
        check(re.search(r"^    ports:\s*$", wb, re.M) is None,
              "base: workbench publishes NO host port")
        check("workbench" in wb and "all" in wb and
              re.search(r"^    profiles:", wb, re.M) is not None,
              "base: workbench gated behind the workbench/all profile")
        check(re.search(r"^    build:", wb, re.M) is None,
              "base: workbench is IMAGE-ONLY (no build section)")
        check("ghcr.io/nexuslbs/workbench:latest" in wb,
              "base: default image is the published core image")
        check("workbench-cache:" in wb,
              "base: workbench-cache named volume still mounted")
        check("OMNI_DIR:" in wb,
              "base: OMNI_DIR exported for the container transport")
        check("COMPOSE_PROJECT_NAME:" in wb,
              "base: COMPOSE_PROJECT_NAME exported for the container transport")

    # ---- 3. DEV overlay: local build + dev-only host port -------------------
    dev = read("docker-compose.dev.yml")
    wbd = service_block(dev, "workbench")
    check(bool(wbd), "docker-compose.dev.yml overrides the workbench service")
    if wbd:
        check("context: ./services/workbench" in wbd,
              "dev: workbench built from services/workbench")
        check("local/workbench:latest" in wbd,
              "dev: workbench tagged local/workbench:latest")
        check('"12347:8080"' in wbd or "12347:8080" in wbd,
              "dev: workbench published on host 12347 only")

    print()
    if FAILURES:
        print("FAILED (%d):" % len(FAILURES))
        for failure in FAILURES:
            print("  - " + failure)
        return 1
    print("OK: workbench service docker+ssh invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())

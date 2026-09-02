# Reliable Docker Desktop start on this PC

Windows build 26200 can leave Docker Desktop's Windows AF_UNIX runtime sockets as inaccessible NTFS reparse points. Docker then crashes before its WSL engine starts while trying to remove either:

- `%LOCALAPPDATA%\Docker\run\dockerInference`
- `%LOCALAPPDATA%\docker-secrets-engine\engine.sock`

Use `start-docker-reliable.ps1` (or the **Docker Desktop (Reliable Start)** shortcut on the Windows desktop). It:

1. returns immediately when the Docker API is already healthy;
2. stops only unresponsive Docker Desktop processes;
3. renames the two small runtime directories when stale entries exist;
4. creates clean runtime directories;
5. starts Docker Desktop and waits for a responsive Linux engine.

It does not reset Docker Desktop, unregister WSL distributions, prune Docker data, or alter images, volumes, builders, and containers. Renamed runtime directories are retained with `.stale-<timestamp>` names because Windows cannot address the corrupted reparse points inside them.

Verification performed on 2026-08-31:

- Docker Desktop became ready in about eight seconds through the repaired path.
- Docker Engine 29.6.2 responded normally.
- `hello-world` completed successfully after a cold repair start.

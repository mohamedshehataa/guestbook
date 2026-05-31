# Guestbook — A Hardened Multi-Container Web App

A small but production-patterned three-tier web application, built to demonstrate containerization and DevSecOps fundamentals: container hardening, network segmentation, secrets management, and vulnerability scanning.

> This is a learning project. The emphasis is less on the app itself (a simple guestbook) and more on **operating it the way a real production service would be run** — secured, observable, and reproducible.

---

## Architecture

Three containers, each with a single responsibility, communicating over a private Docker network:

```
                    ┌──────────────────────────────────────────────┐
                    │  Host (Ubuntu Server)                        │
                    │                                              │
 Browser ──:8080──▶│  ┌─────────────┐   ┌─────────────┐           │
                    │  │  frontend   │──▶│   backend   │──┐        │
                    │  │  (nginx)    │   │  (Flask)    │  │        │
                    │  │  :8080      │   │  :5000      │  │        │
                    │  └─────────────┘   └─────────────┘  │        │
                    │                                     ▼        │
                    │                              ┌─────────────┐ │
                    │                              │     db      │ │
                    │                              │ (Postgres)  │ │
                    │                              │  :5432      │ │
                    │                              └──────┬──────┘ │
                    │                                     │        │
                    │                              ┌──────▼──────┐ │
                    │                              │  Volume:    │ │
                    │                              │  db_data    │ │
                    │                              └─────────────┘ │
                    └──────────────────────────────────────────────┘

         Only the frontend is published to the host.
         backend and db are reachable only on the internal network.
```

| Service | Tech | Role | Exposed? |
|---------|------|------|----------|
| `frontend` | nginx (unprivileged, alpine) | Serves static UI, reverse-proxies `/api/` to backend | Yes — host port 8080 |
| `backend` | Python / Flask | REST API, talks to the database | No — internal only |
| `db` | PostgreSQL 16 (alpine) | Persistent storage | No — internal only |

---

## Running it

Requirements: Docker Engine + Docker Compose plugin.

```bash
# 1. Create the secrets file (not committed to git)
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)" > .env

# 2. Build and start
docker compose up -d --build

# 3. Verify all services are healthy
docker compose ps

# 4. Open the app
#    http://localhost:8080   (or http://<host-ip>:8080)
```

To tear down:

```bash
docker compose down        # stop containers, keep data
docker compose down -v     # stop containers AND delete the data volume
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/entries` | List all guestbook entries (newest first) |
| `POST` | `/api/entries` | Add an entry — JSON body `{"name": "...", "message": "..."}` |
| `GET` | `/health` | Backend health endpoint (used by container healthcheck) |

---

## Security hardening

This is the heart of the project. Each measure addresses a specific threat.

### Container hardening

| Measure | Implementation | Threat addressed |
|---------|----------------|------------------|
| **Non-root execution** | Frontend uses `nginxinc/nginx-unprivileged`; backend defines a dedicated `app` user | Limits damage from a container compromise; container escape is harder from a non-root process |
| **Read-only root filesystem** | `read_only: true` on the frontend, with a `tmpfs` mount for runtime temp files | An attacker who compromises nginx cannot write malware, web shells, or modify served content |
| **Dropped capabilities** | `cap_drop: ALL` + `security_opt: no-new-privileges` | Removes all Linux capabilities the app doesn't need; blocks privilege escalation |
| **Resource limits** | CPU and memory caps per service via `deploy.resources.limits` | Prevents one container (e.g. a memory leak or DoS) from exhausting host resources |
| **Healthchecks** | Each service self-reports health; orchestrator can auto-restart unhealthy containers | Detects "running but broken" states; enables self-healing |

### Network segmentation

- Only the `frontend` publishes a port to the host. The `backend` and `db` are reachable **only** on the internal Docker network.
- This enforces a layered architecture: an attacker must compromise the frontend, then pivot through the backend, before ever reaching the database — and the database is never directly exposed to the outside world.

### Secrets management

- The database password is supplied via a `.env` file, which is **git-ignored** and never committed.
- `docker-compose.yml` references the secret as `${POSTGRES_PASSWORD}` — no plaintext credentials in version control.
- *(Production note: the next step beyond this would be Docker secrets mounted as files, or an external secrets manager such as HashiCorp Vault / AWS Secrets Manager.)*

### Image & dependency scanning

Images and source are scanned with [Trivy](https://github.com/aquasecurity/trivy):

```bash
# Scan a built image for OS + library CVEs
trivy image --severity HIGH,CRITICAL guestbook-frontend

# Scan source for vulnerable deps, leaked secrets, and Dockerfile misconfigurations
trivy fs --scanners vuln,secret,misconfig .

# Lint a Dockerfile for security best-practice violations
trivy config frontend/Dockerfile
```

**Results after hardening:**
- Frontend image: reduced from 24 findings (2 CRITICAL) to 1 (a low-risk, non-reachable HTTP/2 DoS with no fix yet upstream).
- Dockerfile config scan: 0 misconfigurations (non-root user present, healthcheck defined, version pinned).

---

## DevSecOps decisions worth noting

A few choices that reflect production thinking rather than tutorial defaults:

- **Pinned image versions** (`postgres:16-alpine`, `nginx-unprivileged:1.29-alpine`) — never `latest`, so builds are reproducible and don't silently change.
- **Alpine base images** — smaller attack surface and fewer CVEs than full distributions.
- **Risk-based vuln triage** — the single remaining CVE was assessed (DoS only, requires HTTP/2 which isn't enabled, fix not yet upstream) and accepted with documentation, rather than blocking on a non-issue.
- **Dependency-ordered startup** — `depends_on` with `condition: service_healthy` ensures the backend only starts once Postgres is genuinely ready, not merely "started."
- **Healthcheck baked into the image** (`HEALTHCHECK` in the Dockerfile) so it travels with the image regardless of how it's run.

---

## Project structure

```
guestbook/
├── docker-compose.yml      # Orchestration: services, networks, volumes, hardening
├── .env                    # Secrets (git-ignored, not committed)
├── .gitignore
├── backend/
│   ├── Dockerfile          # Python/Flask image, non-root user
│   ├── app.py              # REST API
│   └── requirements.txt
└── frontend/
    ├── Dockerfile          # nginx-unprivileged, read-only-friendly
    ├── nginx.conf          # Serves UI + reverse-proxies /api/
    └── index.html          # Static UI
```

---

## Roadmap / next steps

Things this project is set up to grow into:

- [ ] CI/CD pipeline (GitHub Actions): build → test → Trivy scan → push to registry, with the build failing on critical CVEs
- [ ] Image signing (Cosign) and SBOM generation
- [ ] TLS termination via reverse proxy + Let's Encrypt
- [ ] Migrate secrets to a dedicated secrets manager
- [ ] Deploy to a managed environment (cloud / Kubernetes) with NetworkPolicies enforcing the same segmentation

---

## License

MIT — this is a learning project, use it freely.

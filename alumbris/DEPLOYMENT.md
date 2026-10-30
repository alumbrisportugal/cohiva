# Synology DS220+ deployment guardrails

**Not an installation guide.** Upstream offers Django/PWA Dockerfiles and development Compose files. A reviewed production Compose for the fork does not yet exist.

Target: Synology DS220+, Intel Celeron J4025 (AMD64), 18 GB RAM, Btrfs RAID1 SSD, DSM Container Manager.

- Run within a uniquely named Docker Compose project visible in DSM Container Manager.
- Stage all new containers, secrets, volumes, internal networking and ports independently.
- Never change existing SSH/Synology MCP servers, gateway, shared reverse proxy mappings, or unrelated DSM services.
- Avoid binding development MariaDB/Redis ports (3306, 6379) on the NAS host. Use project-scoped internal networks.
- Do not copy development credentials from `django/docker-compose.dev.yml`; inject new unique secrets outside Git.
- Use HTTPS via explicit, isolated reverse proxy route; do not repurpose the existing MCP route.
- Include Celery/Redis only when required; background workers must be monitored.
- Produce repeatable install, upgrade, healthcheck, backup, restore, rollback and cleanup verification.
- Verify external image compatibility, especially Debian packages / Python wheels on AMD64.
- Test backup restoration, per-tenant isolation, move-out, permissions and legal workflows before deployment.
- Do not treat a successful container startup as commercial acceptance.

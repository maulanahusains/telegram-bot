# Docker assets

The backend Dockerfile lives in `backend/Dockerfile`; its build context is the
`backend/` directory. The workspace-level Compose definition remains at
`../docker-compose.yml` so it can orchestrate PostgreSQL, the backend, the
development Cloudflare Tunnel, and a future frontend. This directory is reserved
for backend deployment-specific extensions such as reverse-proxy configuration.

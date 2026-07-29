# docker/

Supplementary Docker assets that aren't the primary `Dockerfile` or
`docker-compose.yml` (those live at the project root so `docker compose up`
works with zero flags).

This folder is reserved for things that will accumulate as the platform
grows: database init scripts, service-specific Dockerfiles (e.g. a future
`browser` worker image with Playwright + Chromium), and nginx/reverse-proxy
config. Empty for this foundation iteration.

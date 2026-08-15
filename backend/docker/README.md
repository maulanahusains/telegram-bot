# Docker assets

The production image and Compose definition live at the repository root so
`docker compose up --build` works without additional flags. This directory is
reserved for deployment-specific extensions such as reverse-proxy configuration.

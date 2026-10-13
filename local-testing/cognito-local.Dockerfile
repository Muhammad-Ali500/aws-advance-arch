# cognito-local emulates the real AWS Cognito User Pools API for local
# testing - https://github.com/jagregory/cognito-local
# This lets us test the REAL sign-up/sign-in/JWT flow end-to-end locally,
# with zero code changes needed when pointing at real AWS Cognito later.
FROM node:20-slim
WORKDIR /app
RUN npm install -g cognito-local@latest

# cognito-local defaults to binding ::1 (loopback-only inside the
# container), which the host port mapping can't reach. This config
# overrides the server's bind address to 0.0.0.0 while keeping the token
# issuer as "localhost:9229" - the address the host machine (browser,
# backend via host.docker.internal, seed script) actually uses to reach it.
# Config file path/schema confirmed from cognito-local's own source
# (lib/server/defaults.js + lib/services/dataStore/stormDb.js).
RUN mkdir -p /app/.cognito && printf '%s' \
  '{"ServerConfig":{"hostname":"0.0.0.0"},"TokenConfig":{"IssuerDomain":"http://localhost:9229"}}' \
  > /app/.cognito/config.json

EXPOSE 9229
CMD ["cognito-local"]

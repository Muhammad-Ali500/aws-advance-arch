# For LOCAL TESTING ONLY - production deployment is via AWS Amplify Hosting
# directly from the Git repo (no Docker involved there at all). This just
# lets us build + serve the exact same static output locally to verify it
# works before pushing.
#
# Vite bakes VITE_* env vars into the build at BUILD time, not runtime (it's
# a static site) - so these must be passed as --build-arg, not -e.
FROM node:20-slim
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .

ARG VITE_USER_POOL_ID
ARG VITE_USER_POOL_CLIENT_ID
ARG VITE_COGNITO_ENDPOINT
ENV VITE_USER_POOL_ID=$VITE_USER_POOL_ID
ENV VITE_USER_POOL_CLIENT_ID=$VITE_USER_POOL_CLIENT_ID
ENV VITE_COGNITO_ENDPOINT=$VITE_COGNITO_ENDPOINT

RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview"]

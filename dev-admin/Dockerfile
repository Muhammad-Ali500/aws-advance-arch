# For LOCAL TESTING ONLY - production deployment is via AWS Amplify Hosting
# directly from the Git repo. This builds + serves the same static output.
# Vite bakes VITE_* env vars in at BUILD time, so pass them as --build-arg.
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build
EXPOSE 5174
CMD ["npm", "run", "preview"]

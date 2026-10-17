# For LOCAL TESTING ONLY - production is AWS Amplify Hosting (SSR) from Git.
# NEXT_PUBLIC_* values are inlined at BUILD time, so pass them as --build-arg.
FROM node:20-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build
EXPOSE 3001
CMD ["npm", "run", "start"]

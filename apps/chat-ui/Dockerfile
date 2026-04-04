FROM node:20-alpine

WORKDIR /app
COPY apps/chat-ui/package.json ./
RUN npm install
COPY apps/chat-ui/ ./
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


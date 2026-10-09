FROM node:22-bookworm-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV PORT=65525
ENV HOSTNAME=0.0.0.0
EXPOSE 65525

CMD ["npm", "start"]

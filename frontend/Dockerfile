# Dev-mode image (matches docker-compose.yml, which maps 5173 -> the
# Vite dev server with hot reload). For a production build, run
# `npm run build` and serve dist/ from a static host (Vercel today --
# see docs/CURRENT_STATE.md) rather than from this image.
FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

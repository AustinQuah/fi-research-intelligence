# ============================================================
# Stage 1: Build React frontend
# ============================================================

FROM node:24-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json ./
COPY frontend/package-lock.json* ./

RUN npm install

COPY frontend/ ./

RUN npm run build


# ============================================================
# Stage 2: Python backend + built frontend
# ============================================================

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy compiled React application
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]

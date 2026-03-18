# =========================
# Imagen base Python
# =========================
FROM python:3.13-slim

# =========================
# Variables de entorno
# =========================
ENV PLAYWRIGHT_BROWSERS_PATH=0
ENV PYTHONUNBUFFERED=1

# =========================
# Instalar dependencias del sistema
# =========================
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libx11-xcb1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxrandr2 \
    libxdamage1 \
    libgbm1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxshmfence1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    wget \
    ca-certificates \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Crear directorio del proyecto
# =========================
WORKDIR /app

# =========================
# Copiar requerimientos y bot
# =========================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# =========================
# Instalar navegadores de Playwright
# =========================
RUN playwright install chromium

# =========================
# Comando por defecto
# =========================
CMD ["python", "bot.py"]
#!/bin/bash
set -e

echo "🚀 Iniciando build..."

# Atualizar sistema
apt-get update -y

# Instalar dependências do sistema
apt-get install -y \
    wget \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    jq \
    curl \
    gnupg \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils

# Instalar Chrome
echo "📦 Instalando Google Chrome..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
apt-get update -y
apt-get install -y google-chrome-stable

# Instalar ChromeDriver compatível
echo "📦 Instalando ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1-3)
wget -O chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
unzip chromedriver.zip
mv chromedriver-linux64/chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

# Verificar instalações
echo "✅ Chrome: $(google-chrome --version)"
echo "✅ ChromeDriver: $(chromedriver --version)"

# Instalar dependências Python
echo "📦 Instalando dependências Python..."
pip install -r requirements.txt

echo "✅ Build concluído com sucesso!"

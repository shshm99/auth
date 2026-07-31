FROM python:3.10-slim

# Install Google Chrome dan dependencies yang diperlukan untuk paparan grafik
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor | tee /usr/share/keyrings/google-chrome.gpg > /dev/null \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy semua fail ke dalam container
COPY . .

# Install Python packages dan Playwright browser
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Expose port untuk Flask
EXPOSE 8080

# Jalankan Xvfb (skrin hantu) dan start bot Python
CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & export DISPLAY=:99 && python app.py"]

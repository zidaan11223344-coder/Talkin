FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    nodejs \
    tesseract-ocr \
    tesseract-ocr-ara \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN echo "=== CHECK TREASURE FILE ===" \
    && ls -la /app/treasure_mining* \
    && python -c "import os; print('FILE EXISTS:', os.path.isfile('/app/treasure_mining.py'))"

CMD ["python", "bot.py"]
FROM python:3.11-slim

# System dependencies:
# - ffmpeg: audio/video conversion
# - libreoffice-{writer,calc,impress}: document conversion (docx/odt/pptx/xlsx -> pdf, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /tmp/convertmaster

CMD ["python", "bot.py"]

# Dockerfile
# Opisuje kroki budowania obrazu Docker dla aplikacji TibiaVision.

# Użyj oficjalnego, lekkiego obrazu Python jako bazowego
FROM python:3.9-slim

# Ustaw katalog roboczy w kontenerze
WORKDIR /tibia-vision-app

# Zainstaluj niezbędne zależności systemowe
# - libgl1-mesa-glx, libglib2.0-0: wymagane przez OpenCV
# - ffmpeg: wymagane przez yt-dlp do przetwarzania strumieni wideo
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj plik z zależnościami Python
COPY requirements.txt requirements.txt

# Zainstaluj zależności Python
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj resztę kodu aplikacji do katalogu roboczego
COPY ./app ./app
COPY map.png .

# Utwórz katalogi na przesyłane pliki i wyniki
RUN mkdir -p /tibia-vision-app/app/uploads
RUN mkdir -p /tibia-vision-app/app/output

# Ustaw polecenie uruchomieniowe dla kontenera
# Użyj Gunicorn jako serwera aplikacji WSGI
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app.main:app"]

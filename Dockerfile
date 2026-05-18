FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VISION_MODEL_PATH=/models/ppe-detector.pt \
    SAFETY_NET_MODEL_PATH=/models/safety-net-classifier.pt \
    VISION_INPUT_DIR=/data/files \
    VISION_OUTPUT_DIR=/data/vision_results

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY service.py ./service.py
COPY bentofile.yaml ./bentofile.yaml

EXPOSE 8002

CMD ["bentoml", "serve", "service:VisionService", "--host", "0.0.0.0", "--port", "8002"]

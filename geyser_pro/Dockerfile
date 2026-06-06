ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.23
FROM ${BUILD_FROM}

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir requests paho-mqtt

CMD ["python3", "/app/run.py"]
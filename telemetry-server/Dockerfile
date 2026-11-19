FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /service
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

RUN useradd --create-home --uid 10001 telemetry
USER telemetry

CMD ["uvicorn", "app.main:public_app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]

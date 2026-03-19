FROM python:3.11-slim

WORKDIR /app

ENV PIP_ROOT_USER_ACTION=ignore \
    PYTHONUNBUFFERED=1

# Copy service code (build context: demo/Docker-A)
COPY . /app

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir fastapi "uvicorn[standard]" prometheus-client

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]


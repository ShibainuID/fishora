FROM python:3.11-slim

WORKDIR /opt/fishora
COPY . .
RUN pip install --no-cache-dir ".[cv]"

EXPOSE 8001
CMD ["uvicorn", "apps.cv_service.main:app", "--host", "0.0.0.0", "--port", "8001"]

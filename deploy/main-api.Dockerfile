FROM python:3.11-slim

WORKDIR /opt/fishora
COPY . .
RUN pip install --no-cache-dir "."

EXPOSE 8000
CMD ["uvicorn", "apps.main_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

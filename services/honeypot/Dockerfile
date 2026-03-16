FROM python:3.11-slim

WORKDIR /app

COPY honeypot.py .

RUN pip install --no-cache-dir flask prometheus-client requests

# Open both the SSH and HTTP trap ports
EXPOSE 2222 8888

CMD ["python", "honeypot.py"]

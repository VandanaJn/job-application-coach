FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 agentcore
USER agentcore

EXPOSE 8080

COPY main.py .
COPY agents/ ./agents/

CMD ["opentelemetry-instrument", "python", "main.py"]

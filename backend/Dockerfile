# Same runtime contract as the real Slotta backend container:
# port 3000, curl for the ECS health check, GET /health, non-root user.
FROM public.ecr.aws/docker/library/python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./

RUN useradd --uid 1001 appuser
USER appuser

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://127.0.0.1:3000/health || exit 1

# keep-alive longer than the ALB idle timeout (120 s) avoids random 502s
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--timeout-keep-alive", "130"]

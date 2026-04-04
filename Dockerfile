# Saarthi AI — Learning Agent
# Deploys as a serverless container to Google Cloud Run.
# Cloud Run uses the IAM service account for AlloyDB and Vertex AI auth.
# No credentials are baked into the image.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY agents/   ./agents/
COPY tools/    ./tools/
COPY db/       ./db/
COPY models/   ./models/
COPY main.py   .

# Cloud Run listens on PORT (default 8080)
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
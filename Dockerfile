FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set environment variables
ENV PORT=8080
ENV APP_ENV=production

# Cloud Run binds to 8080 by default
EXPOSE 8080

# Use exec form for faster signals handling
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
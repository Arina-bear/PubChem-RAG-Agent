FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy services directory for embedder and search
COPY ../../services /opt/researchai/services

EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8000"]
FROM python:3.11-slim

# Keep Python lean and logs unbuffered.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

EXPOSE 8000

# Default command is overridden by docker-compose (migrate + seed + serve),
# but this makes the image runnable on its own too.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

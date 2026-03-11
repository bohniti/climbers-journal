FROM python:3.12-slim

WORKDIR /app

# System deps for Pillow (JPEG, PNG support for EXIF extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY . .

# Create uploads directory (mounted as Docker volume in production)
RUN mkdir -p /app/uploads/photos

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

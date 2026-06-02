FROM python:3.11-alpine

# Create non-root user (Alpine uses adduser, not useradd)
RUN adduser -D -s /bin/sh app

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY app.py .

# Drop privileges
USER app

EXPOSE 5000

CMD ["python", "app.py"]

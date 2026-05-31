FROM python:3.11-slim

# Create non-root user (DevSecOps habit!)
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY app.py .

# Drop privileges
USER app

EXPOSE 5000

CMD ["python", "app.py"]

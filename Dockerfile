FROM python:3.11-slim

# Set working directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy project files
COPY backend ./backend/
COPY frontend ./frontend/

# Expose port
EXPOSE 8000

# Set working directory for the server
WORKDIR /usr/src/app/backend

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

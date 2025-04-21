# Stage 1: Builder
FROM python:3.10-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /microservice

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies into a specific directory
# Using --prefix prevents mixing with system packages and makes copying easier
RUN pip install --upgrade pip
RUN pip install --prefix=/install -r requirements.txt


# Stage 2: Final image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /microservice

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

# Copy necessary application code
# Adjust these lines based on your actual project structure
COPY ./app /microservice/app
# COPY run.py /microservice/run.py # Uncomment if you have run.py
# COPY other_needed_files /microservice/other_needed_files

# Ensure the user running the application has permissions if needed
# RUN useradd --create-home appuser && chown -R appuser:appuser /microservice
# USER appuser # Optional: run as non-root user

# Make port 8889 available
EXPOSE 8889

# Define the command to run your app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8889"] 
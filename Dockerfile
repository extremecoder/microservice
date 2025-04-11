# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /microservice

# Install system dependencies that might be needed by some Python packages
# (Add any other dependencies if needed, e.g., build-essential for C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy the entire project directory contents into /microservice
COPY . /microservice

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /microservice
# Copy the main application directory
# COPY ./app /microservice/app # Removed
# Copy any other necessary files/directories from the root if needed
# COPY test_circuit.qasm /microservice/test_circuit.qasm # Removed
# COPY run.py /microservice/run.py # Uncomment if run.py is the entry point

# Make port 8889 available to the world outside this container
EXPOSE 8889

# Define the command to run your app using uvicorn
# Adjust the entry point 'app.main:app' if your main FastAPI app instance is located elsewhere
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8889"] 
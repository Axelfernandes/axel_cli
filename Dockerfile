# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements and app from the backend directory
# This assumes the build context is the repository root
COPY backend/requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY backend/app /app/app

# Port is handled by Cloud Run dynamically, we don't strictly need EXPOSE but it's good practice.
EXPOSE 8080

# Run uvicorn to serve the FastAPI app
# Cloud Run provides the PORT environment variable.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

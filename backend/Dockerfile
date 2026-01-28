# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./app /app/app
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Port is handled by Cloud Run dynamically, we don't strictly need EXPOSE but it's good practice.
# However, Cloud Run defaults to 8080 if not specified.
EXPOSE 8080

# Run uvicorn to serve the FastAPI app
# Cloud Run provides the PORT environment variable.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

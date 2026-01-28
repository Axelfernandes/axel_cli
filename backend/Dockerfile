# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./app /app/app
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run uvicorn to serve the FastAPI app
# For Cloud Run, the command should be `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
# We'll use 8000 as a default for local testing, Cloud Run will override $PORT
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

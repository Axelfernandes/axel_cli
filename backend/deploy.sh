#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
SERVICE_NAME="axel-backend"
# Read environment variables from .env.cloudrun
if [ -f ".env.cloudrun" ]; then
    export $(cat .env.cloudrun | xargs)
else
    echo "Error: .env.cloudrun not found. Please create it with environment variables."
    exit 1
fi

# Ensure GOOGLE_CLOUD_PROJECT_ID is set in the environment where the script is run
if [ -z "$GOOGLE_CLOUD_PROJECT_ID" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT_ID environment variable not set."
    echo "Please set it before running this script (e.g., export GOOGLE_CLOUD_PROJECT_ID=your-project-id)."
    exit 1
fi

# Ensure GOOGLE_CLOUD_REGION is set (from .env.cloudrun)
if [ -z "$GOOGLE_CLOUD_REGION" ]; then
    echo "Error: GOOGLE_CLOUD_REGION not found in .env.cloudrun or not set."
    exit 1
fi

# Construct the full image name
IMAGE_NAME="gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${SERVICE_NAME}"

# --- Authenticate Docker to GCR (if not already) ---
echo "Authenticating Docker to Google Container Registry..."
gcloud auth configure-docker

# --- Build and Push Docker Image ---
echo "Building and pushing Docker image: ${IMAGE_NAME}"
gcloud builds submit --tag "${IMAGE_NAME}" .

# --- Deploy to Cloud Run ---
echo "Deploying ${SERVICE_NAME} to Cloud Run in region ${GOOGLE_CLOUD_REGION}..."

# Prepare environment variables for Cloud Run
ENV_VARS_STRING="GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION},GOOGLE_CLOUD_PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID}"
if [ -n "$VERTEX_MODEL_NAME" ]; then
    ENV_VARS_STRING="${ENV_VARS_STRING},VERTEX_MODEL_NAME=${VERTEX_MODEL_NAME}"
fi
if [ -n "$VERTEX_MODEL_VERSION" ]; then
    ENV_VARS_STRING="${ENV_VARS_STRING},VERTEX_MODEL_VERSION=${VERTEX_MODEL_VERSION}"
fi

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}" \
  --platform managed \
  --region "${GOOGLE_CLOUD_REGION}" \
  --allow-unauthenticated \
  --set-env-vars "${ENV_VARS_STRING}" \
  --project "${GOOGLE_CLOUD_PROJECT_ID}" \
  --port 8080 \
  --quiet

echo "Deployment complete. The service URL will be shown in the gcloud output above."
echo "Remember to update the CLI's --backend-url with the deployed service URL."

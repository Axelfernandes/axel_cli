#!/bin/bash

set -e

SERVICE_NAME="axel-backend"

if [ -f ".env.cloudrun" ]; then
    export $(cat .env.cloudrun | xargs)
else
    echo "Error: .env.cloudrun not found."
    exit 1
fi

if [ -z "$GOOGLE_CLOUD_PROJECT_ID" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT_ID not set."
    exit 1
fi

if [ -z "$GOOGLE_CLOUD_REGION" ]; then
    echo "Error: GOOGLE_CLOUD_REGION not set."
    exit 1
fi

IMAGE_NAME="gcr.io/${GOOGLE_CLOUD_PROJECT_ID}/${SERVICE_NAME}"

echo "Authenticating Docker..."
gcloud auth configure-docker

echo "Building Docker image: ${IMAGE_NAME}"
gcloud builds submit --tag "${IMAGE_NAME}" .

echo "Deploying to Cloud Run..."

ENV_VARS="GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION},GOOGLE_CLOUD_PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID}"
[ -n "$VERTEX_MODEL_NAME" ] && ENV_VARS="${ENV_VARS},VERTEX_MODEL_NAME=${VERTEX_MODEL_NAME}"
[ -n "$VERTEX_MODEL_VERSION" ] && ENV_VARS="${ENV_VARS},VERTEX_MODEL_VERSION=${VERTEX_MODEL_VERSION}"
[ -n "$DATABASE_URL" ] && ENV_VARS="${ENV_VARS},DATABASE_URL=${DATABASE_URL}"
[ -n "$REDIS_URL" ] && ENV_VARS="${ENV_VARS},REDIS_URL=${REDIS_URL}"
[ -n "$GITHUB_CLIENT_ID" ] && ENV_VARS="${ENV_VARS},GITHUB_CLIENT_ID=${GITHUB_CLIENT_ID}"
[ -n "$GITHUB_CLIENT_SECRET" ] && ENV_VARS="${ENV_VARS},GITHUB_CLIENT_SECRET=${GITHUB_CLIENT_SECRET}"
[ -n "$GITHUB_CALLBACK_URL" ] && ENV_VARS="${ENV_VARS},GITHUB_CALLBACK_URL=${GITHUB_CALLBACK_URL}"
[ -n "$FRONTEND_URL" ] && ENV_VARS="${ENV_VARS},FRONTEND_URL=${FRONTEND_URL}"
[ -n "$JWT_SECRET" ] && ENV_VARS="${ENV_VARS},JWT_SECRET=${JWT_SECRET}"
[ -n "$ENCRYPTION_KEY" ] && ENV_VARS="${ENV_VARS},ENCRYPTION_KEY=${ENCRYPTION_KEY}"

gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}" \
  --platform managed \
  --region "${GOOGLE_CLOUD_REGION}" \
  --allow-unauthenticated \
  --set-env-vars "${ENV_VARS}" \
  --project "${GOOGLE_CLOUD_PROJECT_ID}" \
  --port 8080 \
  --quiet

echo "Deployment complete!"

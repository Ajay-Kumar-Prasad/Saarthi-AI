
gcloud config set project mediqueryai
gcloud services enable \
  secretmanager.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
while IFS='=' read -r key value; do
  key="$(printf '%s' "$key" | xargs)"
  case "$key" in
    ''|\#*) continue ;;
  esac

  value="${value%\"}"
  value="${value#\"}"

  printf '%s' "$value" > /tmp/"$key"

  if gcloud secrets describe "$key" >/dev/null 2>&1; then
    gcloud secrets versions add "$key" --data-file=/tmp/"$key"
  else
    gcloud secrets create "$key" --data-file=/tmp/"$key"
  fi
done < .env
gcloud secrets list
Create your runtime service account if needed:

gcloud iam service-accounts create personal-agent-saarthi \
  --display-name="Saarthi runtime service account"
Grant secret access:

gcloud projects add-iam-policy-binding mediqueryai \
  --member="serviceAccount:personal-agent-saarthi@mediqueryai.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None
Grant Artifact Registry read:

gcloud projects add-iam-policy-binding mediqueryai \
  --member="serviceAccount:personal-agent-saarthi@mediqueryai.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.reader" \
  --condition=None
Create Artifact Registry repo once:

gcloud artifacts repositories create saarthi \
  --repository-format=docker \
  --location=europe-west1
Build backend image from repo root:

gcloud builds submit . \
  --tag "europe-west1-docker.pkg.dev/mediqueryai/saarthi/saarthi-api"
Deploy backend:

gcloud run deploy saarthi-api \
  --image "europe-west1-docker.pkg.dev/mediqueryai/saarthi/saarthi-api" \
  --project "mediqueryai" \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account "personal-agent-saarthi@mediqueryai.iam.gserviceaccount.com" \
  --set-secrets ALLOYDB_INSTANCE_URI=ALLOYDB_INSTANCE_URI:latest,MOCK_DB=MOCK_DB:latest,GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest,DB_HOST=DB_HOST:latest,DB_PORT=DB_PORT:latest,DB_USER=DB_USER:latest,DB_PASS=DB_PASS:latest,DB_NAME=DB_NAME:latest,DB_SSL=DB_SSL:latest,ALLOYDB_PUBLIC_IP=ALLOYDB_PUBLIC_IP:latest,GCP_PROJECT_ID=GCP_PROJECT_ID:latest,GCP_REGION=GCP_REGION:latest,ALLOYDB_CLUSTER=ALLOYDB_CLUSTER:latest,ALLOYDB_INSTANCE=ALLOYDB_INSTANCE:latest,EMBEDDING_MODEL_ID=EMBEDDING_MODEL_ID:latest,NEXT_PUBLIC_APP_NAME=NEXT_PUBLIC_APP_NAME:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,CALENDER_KEY=CALENDER_KEY:latest,REFRESH_TOKEN=REFRESH_TOKEN:latest,API_URL=API_URL:latest,MCP_SERVER_URL=MCP_SERVER_URL:latest,MCP_AUTH_TOKEN=MCP_AUTH_TOKEN:latest,MOCK_WORKSPACE_MCP=MOCK_WORKSPACE_MCP:latest,PROJECT_ID=PROJECT_ID:latest,PROJECT_NUMBER=PROJECT_NUMBER:latest,SA_NAME=SA_NAME:latest,SERVICE_ACCOUNT=SERVICE_ACCOUNT:latest,MODEL=MODEL:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,GOOGLE_FIT_REFRESH_TOKEN=GOOGLE_FIT_REFRESH_TOKEN:latest,GOOGLE_REDIRECT_URI=GOOGLE_REDIRECT_URI:latest,ALLOYDB_HOST=ALLOYDB_HOST:latest,ALLOYDB_PORT=ALLOYDB_PORT:latest,ALLOYDB_DATABASE=ALLOYDB_DATABASE:latest,ALLOYDB_USER=ALLOYDB_USER:latest,FRONTEND_URL=FRONTEND_URL:latest
Get backend URL:

gcloud run services describe saarthi-api \
  --project "mediqueryai" \
  --region europe-west1 \
  --format='value(status.url)'
Build frontend:

gcloud builds submit frontend \
  --tag "europe-west1-docker.pkg.dev/mediqueryai/saarthi/saarthi-frontend"
Deploy frontend:
Replace the backend URL below with the actual one returned above.

gcloud run deploy saarthi-frontend \
  --image "europe-west1-docker.pkg.dev/mediqueryai/saarthi/saarthi-frontend" \
  --project "mediqueryai" \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars BACKEND_URL=https://YOUR_BACKEND_URL,API_URL=https://YOUR_BACKEND_URL,FRONTEND_URL=https://YOUR_FRONTEND_URL,NEXT_PUBLIC_APP_URL=https://YOUR_FRONTEND_URL
Get frontend URL:

gcloud run services describe saarthi-frontend \
  --project "mediqueryai" \
  --region europe-west1 \
  --format='value(status.url)'
Update FRONTEND_URL secret to the real frontend URL:

printf 'https://YOUR_FRONTEND_URL' | gcloud secrets create FRONTEND_URL --data-file=-
If it already exists:

printf 'https://YOUR_FRONTEND_URL' | gcloud secrets versions add FRONTEND_URL --data-file=-
Rebuild backend if needed:

gcloud builds submit . \
  --tag "europe-west1-docker.pkg.dev/mediqueryai/saarthi/saarthi-api"
Redeploy backend again so OAuth uses the real frontend URL:

gcloud run deploy saarthi-api \
  --image "europe-west1-docker.pkg.dev/mediqueryai/saarthi/saarthi-api" \
  --project "mediqueryai" \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account "personal-agent-saarthi@mediqueryai.iam.gserviceaccount.com" \
  --set-secrets ALLOYDB_INSTANCE_URI=ALLOYDB_INSTANCE_URI:latest,MOCK_DB=MOCK_DB:latest,GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest,DB_HOST=DB_HOST:latest,DB_PORT=DB_PORT:latest,DB_USER=DB_USER:latest,DB_PASS=DB_PASS:latest,DB_NAME=DB_NAME:latest,DB_SSL=DB_SSL:latest,ALLOYDB_PUBLIC_IP=ALLOYDB_PUBLIC_IP:latest,GCP_PROJECT_ID=GCP_PROJECT_ID:latest,GCP_REGION=GCP_REGION:latest,ALLOYDB_CLUSTER=ALLOYDB_CLUSTER:latest,ALLOYDB_INSTANCE=ALLOYDB_INSTANCE:latest,EMBEDDING_MODEL_ID=EMBEDDING_MODEL_ID:latest,NEXT_PUBLIC_APP_NAME=NEXT_PUBLIC_APP_NAME:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,CALENDER_KEY=CALENDER_KEY:latest,REFRESH_TOKEN=REFRESH_TOKEN:latest,API_URL=API_URL:latest,MCP_SERVER_URL=MCP_SERVER_URL:latest,MCP_AUTH_TOKEN=MCP_AUTH_TOKEN:latest,MOCK_WORKSPACE_MCP=MOCK_WORKSPACE_MCP:latest,PROJECT_ID=PROJECT_ID:latest,PROJECT_NUMBER=PROJECT_NUMBER:latest,SA_NAME=SA_NAME:latest,SERVICE_ACCOUNT=SERVICE_ACCOUNT:latest,MODEL=MODEL:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,GOOGLE_FIT_REFRESH_TOKEN=GOOGLE_FIT_REFRESH_TOKEN:latest,GOOGLE_REDIRECT_URI=GOOGLE_REDIRECT_URI:latest,ALLOYDB_HOST=ALLOYDB_HOST:latest,ALLOYDB_PORT=ALLOYDB_PORT:latest,ALLOYDB_DATABASE=ALLOYDB_DATABASE:latest,ALLOYDB_USER=ALLOYDB_USER:latest,FRONTEND_URL=FRONTEND_URL:latest
Google OAuth config:

Authorized JavaScript origin:
https://YOUR_FRONTEND_URL
Authorized redirect URI:
https://YOUR_BACKEND_URL/auth/google/callback
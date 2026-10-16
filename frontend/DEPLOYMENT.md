# CityPulse deployment notes

## Vercel frontend
- Root directory: `frontend`
- Install command: `yarn install --non-interactive`
- Build command: `DISABLE_ESLINT_PLUGIN=true CI=false yarn run build`
- Output directory: `build`
- Required frontend build variable: `REACT_APP_BACKEND_URL`, pointing at the public FastAPI base URL (without the `/api` suffix).

The ESLint webpack plugin is disabled for this deploy build to prevent the existing lint-only build failure from blocking the preview. Run ESLint separately and fix the reported issues before treating this as a production-quality release.

## Vercel backend runtime variables
Required for startup:
- `MONGO_URL`: a real MongoDB connection URI
- `DB_NAME`: database name
- `CORS_ORIGINS`: comma-separated, exact frontend origins

Required by specific features:
- `CITYPULSE_DEMO_PASSWORD`
- `CITYPULSE_OWNER_EMAIL` (optional seed contact)
- `CITYPULSE_STORAGE_PREFIX`
- `EMERGENT_LLM_KEY` for evidence storage integration
- `INTEGRATION_PROXY_URL` is optional

Do not commit secrets into this repository. Configure connection strings and API keys in Vercel Project Settings > Environment Variables, then redeploy the backend.

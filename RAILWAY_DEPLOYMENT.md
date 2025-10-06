# Railway Deployment Guide

## Required Environment Variables

Set these in your Railway project settings:

### API Keys (Required)
- `ANTHROPIC_API_KEY` - Your Anthropic API key for Claude models
- `GOOGLE_API_KEY` - Your Google API key for Gemini models

### Optional Configuration
- `PORT` - Railway provides this automatically (default: 8000)
- `STREAM_TIMEOUT_SECONDS` - Timeout for streaming responses (default: 60)
- `LOG_LEVEL` - Logging level (default: INFO)

## Deployment Steps

1. **Push to GitHub**
   ```bash
   git add railway.json nixpacks.toml RAILWAY_DEPLOYMENT.md railway-env-import.sh
   git commit -m "Add Railway deployment configuration"
   git push origin main
   ```

2. **Create Railway Project**
   - Go to [Railway](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure Environment Variables**

   **Option A: Using the Helper Script (Recommended)**
   ```bash
   # First, link your project
   railway link

   # Import all variables from .env file
   ./railway-env-import.sh
   ```

   **Option B: Manual Configuration**
   - In Railway dashboard, go to your project
   - Click on the service
   - Go to "Variables" tab
   - Add the required API keys

4. **Deploy**
   - Railway will automatically deploy when you push to main
   - Monitor the deployment logs for any issues

## Files Used for Deployment

- `railway.json` - Railway-specific configuration
- `nixpacks.toml` - Build configuration for uv support
- `pyproject.toml` - Python dependencies
- `src/model_comparison/app.py` - Main FastAPI application

## Health Check

The app includes a health endpoint at `/health` that Railway uses to verify the deployment is working.

## Local Testing

To test the deployment configuration locally:

```bash
PYTHONPATH=src uv run uvicorn model_comparison.app:app --host 0.0.0.0 --port 8000
```

Then visit http://localhost:8000

## Troubleshooting

If deployment fails:

1. Check Railway build logs for errors
2. Verify all environment variables are set
3. Ensure pyproject.toml has all required dependencies
4. Check that the health endpoint responds correctly
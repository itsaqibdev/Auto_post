# Deploying to Vercel

## Prerequisites
- Vercel account (sign up at https://vercel.com)
- Vercel CLI (optional, for command-line deployment)

## Deployment Methods

### Method 1: Deploy via Vercel Dashboard (Easiest)

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Import to Vercel**
   - Go to https://vercel.com/new
   - Import your GitHub repository
   - Vercel will auto-detect the Python project
   - Click "Deploy"

### Method 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Deploy**
   ```bash
   vercel
   ```

3. **Follow the prompts:**
   - Set up and deploy? Yes
   - Which scope? Select your account
   - Link to existing project? No
   - What's your project name? news-card-api
   - In which directory is your code located? ./
   - Deploy? Yes

## API Endpoints (After Deployment)

Your API will be available at: `https://YOUR_PROJECT.vercel.app`

### Endpoints:
- `GET /api/news-card` - Generate news card image (returns PNG)
- `GET /api/news-data` - Get news data as JSON
- `GET /health` - Health check

### Example Usage:
```bash
# Get the image
curl https://YOUR_PROJECT.vercel.app/api/news-card --output news.png

# Get JSON data
curl https://YOUR_PROJECT.vercel.app/api/news-data
```

## Important Notes

1. **Serverless Functions**: Vercel runs Python as serverless functions with:
   - 10-second execution timeout (Hobby plan)
   - 50MB response size limit
   - Stateless environment (no file system persistence)

2. **Cold Starts**: First request may be slower due to cold start

3. **Environment Variables**: If you need to add API tokens:
   - Go to Project Settings → Environment Variables
   - Add your variables
   - Redeploy

4. **Custom Domain**: 
   - Go to Project Settings → Domains
   - Add your custom domain

## Testing Locally

Run the server locally before deploying:
```bash
python3 server.py
```

Visit: http://localhost:3000/api/news-card

## Troubleshooting

- **Deployment fails**: Check the build logs in Vercel dashboard
- **Image not loading**: Check CORS settings and API timeout
- **Out of memory**: Reduce image size or quality in server.py

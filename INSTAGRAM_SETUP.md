# Instagram Auto-Posting Setup Guide

This guide will help you set up Instagram auto-posting using the Facebook Graph API.

## Prerequisites

1. **Instagram Business or Creator Account** (Personal accounts won't work)
2. **Facebook Page** connected to your Instagram account
3. **Facebook Developer Account**

## Step 1: Convert Instagram to Business Account

1. Open Instagram app
2. Go to Settings → Account → Switch to Professional Account
3. Choose Business or Creator
4. Connect to a Facebook Page (create one if needed)

## Step 2: Create Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click "My Apps" → "Create App"
3. Select "Business" as app type
4. Fill in:
   - App Name: "News Card Poster" (or your choice)
   - App Contact Email: your email
5. Click "Create App"

## Step 3: Configure Facebook App

1. In your app dashboard, go to "Add Product"
2. Add "Instagram" product
3. Go to Settings → Basic:
   - Add App Domains: `your-domain.vercel.app`
   - Save changes

## Step 4: Get Access Token

### Method 1: Using Graph API Explorer (Temporary - for testing)

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from dropdown
3. Click "Generate Access Token"
4. Add these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `pages_show_list`
5. Click "Generate Access Token" and approve
6. Copy the token (this is temporary, expires in ~1 hour)

### Method 2: Long-Lived Access Token (Recommended)

1. Get a short-lived token from Graph API Explorer (above)
2. Exchange it for long-lived token using this API call:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

3. This gives you a 60-day token
4. To make it permanent, connect to a Page token (doesn't expire)

### Method 3: Page Access Token (Never Expires - Best)

```bash
# 1. Get your User ID
curl "https://graph.facebook.com/v18.0/me?access_token=YOUR_LONG_LIVED_TOKEN"

# 2. Get Page Access Token
curl "https://graph.facebook.com/v18.0/USER_ID/accounts?access_token=YOUR_LONG_LIVED_TOKEN"

# 3. Use the page access_token from response
```

## Step 5: Get Instagram Business Account ID

```bash
curl "https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_PAGE_ACCESS_TOKEN"
```

From the response, find your page, then:

```bash
curl "https://graph.facebook.com/v18.0/PAGE_ID?fields=instagram_business_account&access_token=YOUR_PAGE_ACCESS_TOKEN"
```

Copy the `instagram_business_account.id` - this is your Instagram Business Account ID.

## Step 6: Set Environment Variables

### For Local Development:

Create a `.env` file:
```bash
INSTAGRAM_ACCESS_TOKEN=your_access_token_here
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_business_account_id_here
```

Then load it in your code or export:
```bash
export INSTAGRAM_ACCESS_TOKEN="your_token"
export INSTAGRAM_BUSINESS_ACCOUNT_ID="your_id"
```

### For Vercel Deployment:

1. Go to your Vercel project
2. Settings → Environment Variables
3. Add:
   - `INSTAGRAM_ACCESS_TOKEN` = your token
   - `INSTAGRAM_BUSINESS_ACCOUNT_ID` = your ID
4. Redeploy the project

## Step 7: Test the API

### Check Configuration Status:
```bash
curl http://localhost:3000/api/instagram/status
```

### Post to Instagram:
```bash
# With default caption
curl -X POST http://localhost:3000/api/post-to-instagram \
  -H "Content-Type: application/json"

# With custom caption
curl -X POST http://localhost:3000/api/post-to-instagram \
  -H "Content-Type: application/json" \
  -d '{"caption": "Breaking News! #news #updates"}'
```

## API Endpoints

### 1. Check Instagram Status
```
GET /api/instagram/status
```

Response:
```json
{
  "configured": true,
  "has_access_token": true,
  "has_account_id": true
}
```

### 2. Post to Instagram
```
POST /api/post-to-instagram
```

Request Body (optional):
```json
{
  "caption": "Your custom caption here #hashtags"
}
```

Response:
```json
{
  "success": true,
  "message": "Successfully posted to Instagram",
  "post_id": "123456789",
  "caption": "Your caption",
  "image_url": "https://your-domain.vercel.app/api/news-card"
}
```

## Important Notes

### Instagram API Limitations:

1. **Rate Limits**: 
   - 25 posts per user per day
   - 200 API calls per hour

2. **Image Requirements**:
   - Image must be publicly accessible via HTTPS
   - Supported formats: JPG, PNG
   - Aspect ratio: Between 4:5 and 1.91:1
   - Max file size: 8MB

3. **Account Requirements**:
   - Must be Business or Creator account
   - Must be connected to a Facebook Page
   - Account must not be private

### Troubleshooting:

1. **Error: "Invalid OAuth access token"**
   - Token expired, generate new one
   - Check token has correct permissions

2. **Error: "Instagram account not found"**
   - Verify Instagram Business Account ID
   - Ensure account is connected to Facebook Page

3. **Error: "Image could not be downloaded"**
   - Image URL must be publicly accessible
   - Deploy to Vercel first for public URL
   - Check image format and size

4. **Error: "Too many requests"**
   - Rate limit reached, wait before retrying
   - Implement queue system for bulk posts

## Automated Posting

To automate posting, you can:

1. **Cron Job** (on server):
```bash
0 */3 * * * curl -X POST https://your-domain.vercel.app/api/post-to-instagram
```

2. **GitHub Actions** (in repository):
```yaml
name: Auto Post
on:
  schedule:
    - cron: '0 */3 * * *'  # Every 3 hours
jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - name: Post to Instagram
        run: |
          curl -X POST https://your-domain.vercel.app/api/post-to-instagram
```

3. **Vercel Cron Jobs** (create `vercel.json`):
```json
{
  "crons": [{
    "path": "/api/post-to-instagram",
    "schedule": "0 */3 * * *"
  }]
}
```

## Security Best Practices

1. Never commit access tokens to Git
2. Use environment variables
3. Rotate tokens periodically
4. Use Page tokens (never expire) instead of user tokens
5. Implement error handling and logging
6. Monitor API usage to avoid rate limits

## Resources

- [Instagram Graph API Documentation](https://developers.facebook.com/docs/instagram-api)
- [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)

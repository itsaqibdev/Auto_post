# News Card API

A Python Flask API that generates news card images with styled text overlays and automatically posts them to Instagram.

## Features

- Fetches latest news from TheNewsAPI
- Generates PNG images with news title overlay and gradient effect
- Random word highlighting in green
- Auto-posts to Instagram via Facebook Graph API
- RESTful API endpoints
- Ready for Vercel deployment

## Installation

```bash
pip3 install -r requirements.txt
```

## Usage

Start the server:
```bash
python3 server.py
```

The server will run on http://localhost:3000

## API Endpoints

### 1. Generate News Card Image
```
GET /api/news-card
```
Returns a PNG image of the news card.

**Response:** PNG image file

**Example:**
```bash
curl http://localhost:3000/api/news-card --output news-card.png
```

### 2. Get News Data Only
```
GET /api/news-data
```
Returns JSON with news article data.

**Response:**
```json
{
  "title": "Article title",
  "image_url": "https://...",
  "green_word_indices": [2, 5, 8]
}
```

### 3. Post to Instagram
```
POST /api/post-to-instagram
```
Generates a news card and posts it to Instagram.

**Request Body (optional):**
```json
{
  "caption": "Your custom caption #hashtags"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully posted to Instagram",
  "post_id": "123456789",
  "caption": "Breaking News...",
  "image_url": "https://..."
}
```

### 4. Check Instagram Status
```
GET /api/instagram/status
```
Check if Instagram API is configured.

**Response:**
```json
{
  "configured": true,
  "has_access_token": true,
  "has_account_id": true
}
```

### 5. Health Check
```
GET /health
```
Returns API status.

## Configuration

### Basic Setup

The API runs on port 3000 by default. You can modify the `PORT` in `server.py`.

### Instagram Setup (Optional)

To enable Instagram posting, you need to configure:

1. **Instagram Business Account** connected to a Facebook Page
2. **Facebook Developer App** with Instagram API access
3. **Access Token** and **Business Account ID**

Set these as environment variables:
```bash
export INSTAGRAM_ACCESS_TOKEN="your_token_here"
export INSTAGRAM_BUSINESS_ACCOUNT_ID="your_account_id_here"
```

**For detailed Instagram setup instructions, see [INSTAGRAM_SETUP.md](INSTAGRAM_SETUP.md)**

## Technologies

- **Flask** - Web framework
- **Pillow (PIL)** - Image manipulation and generation
- **Requests** - HTTP client for API calls
- **Facebook Graph API** - Instagram posting

## Deployment

This API is ready to deploy on Vercel. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Vercel deployment guide
- [INSTAGRAM_SETUP.md](INSTAGRAM_SETUP.md) - Instagram API setup guide

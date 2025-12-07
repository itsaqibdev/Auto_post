from flask import Flask, send_file, jsonify, request
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import time
import random
import os
import base64
import json
from datetime import datetime

app = Flask(__name__)

# In-memory cache for posted news (persists during deployment lifetime)
POSTED_NEWS_CACHE = set()

# Posted news tracking file
POSTED_NEWS_FILE = 'posted_news.json'
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f'Warning: Could not save config to file: {e}')
        print('This is expected on Vercel serverless. Use environment variables instead.')
        return False

# Load configuration
config = load_config()

# API Configuration - Load from config.json or use defaults
API_URL = config.get('news_api_url', 'https://api.thenewsapi.com/v1/news/top?api_token=yJ1R0UkzUGsCTQUT7yFGapU6ifGo4GbcXHW5BxQu&locale=pk&limit=3')

# Instagram/Facebook API Configuration
# Priority: Environment variables > config.json > empty string
INSTAGRAM_ACCESS_TOKEN = "EAASZCDdrn0tgBQCteQDMfZCcRZAfYivxuHfjhWJZANEJcZArqtb9nD0hgLax7fG8mgWmQbTVOS5w0ZAsZAjfFrE1YQRBO0pqOlsV2QL04C8Knkr7RF16CrV5ZASrIPhPlzsZBbkJxeeiQTplU5g5WEn66ifFkwQGp5XehAawZAZApMju8eIX8mb4glOHlZAXONps"
INSTAGRAM_BUSINESS_ACCOUNT_ID = "17841478676255587"

def load_posted_news():
    """Load list of already posted news IDs"""
    if os.path.exists(POSTED_NEWS_FILE):
        try:
            with open(POSTED_NEWS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_posted_news(news_id):
    """Save posted news ID to prevent duplicates"""
    # Always add to in-memory cache
    POSTED_NEWS_CACHE.add(news_id)
    print(f'✅ Added to cache: {news_id[:30]}...')
    
    # Try to save to file (works on localhost)
    try:
        posted = load_posted_news()
        if news_id not in posted:
            posted.append(news_id)
            # Keep only last 100 posts to prevent file from growing too large
            if len(posted) > 100:
                posted = posted[-100:]
            with open(POSTED_NEWS_FILE, 'w') as f:
                json.dump(posted, f)
            print(f'💾 Saved to file: {news_id[:30]}...')
    except (OSError, IOError) as e:
        # Handle read-only filesystem (Vercel serverless)
        print(f'⚠️  Read-only filesystem - using cache only')

def is_news_posted(news_id):
    """Check if news has already been posted (uses Instagram as database)"""
    # FIRST: Check in-memory cache (fastest)
    if news_id in POSTED_NEWS_CACHE:
        print(f'🚫 Cache hit: Already posted this session')
        return True
    
    # SECOND: Check local file (works on localhost)
    local_posted = load_posted_news()
    if news_id in local_posted:
        print(f'🚫 File hit: Previously posted')
        POSTED_NEWS_CACHE.add(news_id)
        return True
    
    # THIRD: Check Instagram posts (CRITICAL for Vercel serverless)
    print(f'🔍 Checking Instagram for duplicates...')
    try:
        if INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID:
            url = f"https://graph.facebook.com/v24.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
            params = {
                'access_token': INSTAGRAM_ACCESS_TOKEN,
                'fields': 'caption',
                'limit': 50  # Check last 50 posts
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check if news_id appears in any caption
                for post in data.get('data', []):
                    caption = post.get('caption', '')
                    if f"[ID:{news_id[:20]}]" in caption:
                        print(f'🚫 Instagram hit: Found existing post with same ID')
                        POSTED_NEWS_CACHE.add(news_id)  # Cache it
                        return True
                print(f'✅ Not found in Instagram - safe to post')
            else:
                print(f'⚠️ Instagram check failed: {response.status_code}')
    except Exception as e:
        print(f'⚠️ Instagram check error: {e}')
    
    return False

def get_random_word_indices(words, count=3):
    """Select random words with length > 5 to highlight"""
    indices = []
    long_words = [(i, word) for i, word in enumerate(words) if len(word) > 5]
    
    for _ in range(min(count, len(long_words))):
        if long_words:
            selected = random.choice(long_words)
            indices.append(selected[0])
            long_words.remove(selected)
    
    return indices

def wrap_text(text, font, max_width, draw):
    """Wrap text to fit within specified width with better word wrapping"""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        # Test if adding this word would exceed max width
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(current_line)
                current_line = [word]
            else:
                # If a single word is too long, split it
                current_line = [word]
                while current_line:
                    # Try to fit as much of the word as possible
                    test_word = current_line[0]
                    for i in range(len(test_word), 0, -1):
                        test_fit = test_word[:i] + '-' if i < len(test_word) else test_word
                        bbox = draw.textbbox((0, 0), test_fit, font=font)
                        if (bbox[2] - bbox[0]) <= max_width:
                            lines.append([test_fit])
                            remaining = test_word[i:] if i < len(test_word) else ''
                            if remaining:
                                current_line = [remaining]
                            else:
                                current_line = []
                            break
                    else:
                        # If we can't even fit one character, add the first character and continue
                        lines.append([test_word[0]])
                        current_line = [test_word[1:]] if len(test_word) > 1 else []
    
    # Add any remaining words in the current line
    if current_line:
        lines.append(current_line)
    
    return lines

@app.route('/api/news-card')
def generate_news_card():
    """Generate news card with category, title, and source"""
    # For Vercel deployment, we cannot save to filesystem
    # We'll only return the image directly
    
    try:
        # Step 1: Fetch news data with delay
        print('Step 1: Fetching news data...')
        time.sleep(0.5)  # Initial delay
        
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        article = data['data'][0]
        
        print(f'Step 2: News fetched - {article["title"]}')
        time.sleep(1.0)  # Wait after fetching news
        
        # Get image URL - try direct first, then CORS proxy if needed
        img_url = article['image_url']
        
        print(f'Step 3: Loading image from: {img_url}')
        time.sleep(0.5)  # Wait before loading image
        
        # Download and open image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            # Try direct download first
            img_response = requests.get(img_url, headers=headers, timeout=10)
            img_response.raise_for_status()
            news_image = Image.open(BytesIO(img_response.content))
        except Exception as e:
            print(f'Direct download failed, trying CORS proxy: {e}')
            # Try with CORS proxy
            img_url = f"https://corsproxy.io/?{requests.utils.quote(article['image_url'])}"
            img_response = requests.get(img_url, headers=headers, timeout=15)
            img_response.raise_for_status()
            news_image = Image.open(BytesIO(img_response.content))
        
        # Convert to RGB if necessary (for PNG with transparency)
        if news_image.mode != 'RGB':
            news_image = news_image.convert('RGB')
        
        print('Step 4: Image loaded successfully')
        time.sleep(1.0)  # Wait after image loads
        
        # Step 5: Extract article information
        print('Step 5: Extracting article data...')
        category = article.get('categories', ['News'])[0] if article.get('categories') else 'News'
        source = article.get('source', 'Unknown')
        # Use description if available, otherwise use snippet
        description = article.get('description', '') or article.get('snippet', '')
        time.sleep(0.3)
        
        # Calculate dimensions - Use Instagram-compatible 1:1 aspect ratio
        card_width = 1080
        card_height = 1080
        
        # Step 6: Resize image to cover the square
        print(f'Step 6: Resizing image to {card_width}x{card_height}...')
        # Calculate dimensions to cover the square (crop to fit)
        img_aspect = news_image.width / news_image.height
        if img_aspect > 1:  # Wider than tall
            new_height = card_height
            new_width = int(new_height * img_aspect)
        else:  # Taller than wide
            new_width = card_width
            new_height = int(new_width / img_aspect)
        
        news_image = news_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Crop to center
        left = (new_width - card_width) // 2
        top = (new_height - card_height) // 2
        news_image = news_image.crop((left, top, left + card_width, top + card_height))
        time.sleep(0.3)
        
        print(f'Step 7: Creating canvas...')
        
        # Create canvas
        canvas = Image.new('RGB', (card_width, card_height), (0, 0, 0))
        canvas.paste(news_image, (0, 0))
        
        # Create overlay for gradient effect (only at bottom)
        overlay = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Draw gradient: opaque black at bottom, fades to transparent going up
        overlay_height = 800  # MAXIMUM overlay for huge text (was 700)
        gradient_start = card_height - overlay_height
        
        for i in range(overlay_height):
            y = gradient_start + i
            # i=0 is at top of gradient (transparent), i=overlay_height is at bottom (opaque)
            progress = i / overlay_height  # 0.0 at top of gradient, 1.0 at bottom
            alpha = int(255 * (progress ** 0.7))  # 0 at top, 255 at bottom
            overlay_draw.rectangle([(0, y), (card_width, y + 1)], fill=(0, 0, 0, alpha))
        
        # Convert canvas to RGBA and paste overlay
        canvas = canvas.convert('RGBA')
        canvas = Image.alpha_composite(canvas, overlay)
        canvas = canvas.convert('RGB')
        
        print('Step 8: Drawing gradient overlay...')
        time.sleep(0.2)
        
        # Step 9: Prepare fonts
        print('Step 9: Loading fonts...')
        # Prepare text
        draw = ImageDraw.Draw(canvas)
        
        # Use bundled fonts (works everywhere including Vercel)
        import os
        
        try:
            print('Step 9a: Attempting to load fonts from embedded base64...')
            # Try to load from generated python file (most robust for Vercel)
            try:
                # Import here to avoid top-level errors if file missing
                from fonts_data import ROBOTO_BOLD, ROBOTO_REGULAR
                
                # Load from base64
                title_font_data = base64.b64decode(ROBOTO_BOLD)
                category_font_data = base64.b64decode(ROBOTO_REGULAR)
                
                title_font = ImageFont.truetype(BytesIO(title_font_data), 350)
                category_font = ImageFont.truetype(BytesIO(category_font_data), 150)
                print('✅ Loaded fonts from base64 embedding successfully!')
                
            except Exception as e:
                print(f'⚠️ Base64 font loading failed: {e}')
                
                # Fallback to file system logic
                script_dir = os.path.dirname(os.path.abspath(__file__))
                print(f'📁 Script directory: {script_dir}')
                
                # Define font paths
                font_files = {
                    'title': 'Roboto-Bold.ttf',
                    'category': 'Roboto-Regular.ttf'
                }
                
                loaded_fonts = {}
                
                for font_type, font_filename in font_files.items():
                    # 1. Check local directory (bundled)
                    local_path = os.path.join(script_dir, font_filename)
                    font_path = local_path
                    
                    if not os.path.exists(local_path):
                        print(f'⚠️ {font_filename} not found in script dir')
                        
                        # 2. Check /tmp directory (cached download)
                        tmp_path = os.path.join('/tmp', font_filename)
                        font_path = tmp_path
                        
                        if not os.path.exists(tmp_path):
                            print(f'⚠️ {font_filename} not found in /tmp, downloading...')
                            try:
                                # 3. Download from Google Fonts
                                base_url = "https://github.com/google/fonts/raw/main/apache/roboto/"
                                if font_filename == 'Roboto-Bold.ttf':
                                    url = base_url + "Roboto-Bold.ttf"
                                else:
                                    url = base_url + "Roboto-Regular.ttf"
                                    
                                print(f'⬇️ Downloading {url}...')
                                r = requests.get(url, timeout=10)
                                r.raise_for_status()
                                
                                with open(tmp_path, 'wb') as f:
                                    f.write(r.content)
                                print(f'✅ Downloaded {font_filename} to {tmp_path}')
                            except Exception as e:
                                print(f'❌ Failed to download font: {e}')
                                font_path = None
                    
                    # Load the font
                    if font_path and os.path.exists(font_path):
                        size = 350 if font_type == 'title' else 150
                        try:
                            loaded_fonts[font_type] = ImageFont.truetype(font_path, size)
                            print(f'✅ Loaded {font_type} font from {font_path} at {size}px')
                        except Exception as e:
                            print(f'❌ Failed to load {font_type} font: {e}')
                            loaded_fonts[font_type] = None
                    else:
                        loaded_fonts[font_type] = None

                title_font = loaded_fonts.get('title')
                category_font = loaded_fonts.get('category')

            # Final Fallback to system fonts if everything failed
            if not title_font:
                print('⚠️ Bundled/Downloaded fonts not found, trying system fonts...')
                try:
                    title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 350)
                except:
                    title_font = ImageFont.load_default()
            
            if not category_font:
                try:
                    category_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 150)
                except:
                    category_font = ImageFont.load_default()
                
        except Exception as e:
            print(f'❌ Font loading error: {e}')
            import traceback
            traceback.print_exc()
            title_font = ImageFont.load_default()
            category_font = ImageFont.load_default()
        
        time.sleep(0.2)
        
        # Step 10: Draw category badge
        print(f'Step 10: Adding category badge: {category}')
        category_text = f"  {category.upper()}  "
        cat_bbox = draw.textbbox((0, 0), category_text, font=category_font)
        cat_width = cat_bbox[2] - cat_bbox[0]
        cat_height = cat_bbox[3] - cat_bbox[1]
        
        # Position category badge at top-left corner (scaled for 1080p)
        cat_x = 48  # 48px from left edge
        cat_y = 48  # 48px from top edge
        
        # Draw category background (green badge)
        cat_bg_padding = 16
        draw.rectangle(
            [(cat_x - cat_bg_padding, cat_y - cat_bg_padding), 
             (cat_x + cat_width + cat_bg_padding, cat_y + cat_height + cat_bg_padding)],
            fill=(0, 200, 80)
        )
        
        # Draw category text
        draw.text((cat_x, cat_y), category_text, font=category_font, fill=(255, 255, 255))
        time.sleep(0.2)
        
        # Get words and random indices to highlight
        words = article['title'].split(' ')
        green_indices = get_random_word_indices(words, 3)
        
        # Step 11: Draw title using PIL with LARGE fonts
        print('Step 11: Adding title text...')
        
        # Load large title font (100px)
        title_font_size = 100
        try:
            title_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', title_font_size)
        except:
            try:
                title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', title_font_size)
            except:
                title_font = ImageFont.load_default()
        
        # Wrap text
        max_width = card_width - 96
        words = article['title'].split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=title_font)
            test_width = bbox[2] - bbox[0]
            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate text position
        line_height = 80  # Spacing between lines
        text_height = len(lines) * line_height
        y = card_height - text_height - 30
        
        # Draw title lines
        for line_text in lines:
            words_in_line = line_text.split()
            x = 48
            
            for word in words_in_line:
                # Draw each word (white text)
                draw.text((x, y), word, font=title_font, fill=(255, 255, 255))
                
                # Calculate word width for next position
                bbox = draw.textbbox((0, 0), word, font=title_font)
                word_width = bbox[2] - bbox[0]
                x += word_width + 20  # Add spacing between words
            
            y += line_height
        
        time.sleep(0.2)
        
        # Step 12: Generate PNG
        print('Step 12: Generating PNG...')
        img_io = BytesIO()
        canvas.save(img_io, 'PNG', quality=95)
        img_io.seek(0)
        if os.path.exists('/Users/apple/Downloads/Scripts/n8n'):
            output_path = '/Users/apple/Downloads/Scripts/n8n/news_image.png'
            # Delete old image if it exists
            if os.path.exists(output_path):
                os.remove(output_path)
                print(f'Deleted old image: {output_path}')
            # Save to file
            img_io.seek(0)
            with open(output_path, 'wb') as f:
                f.write(img_io.read())
            print(f'Saved to: {output_path}')
        
        # Reset pointer for sending
        img_io.seek(0)
        
        print('Image sent successfully!')
        
        return send_file(img_io, mimetype='image/png', as_attachment=False, download_name='news_card.png')
        
    except Exception as e:
        print(f'Error generating news card: {str(e)}')
        return jsonify({'error': 'Failed to generate news card', 'message': str(e)}), 500

@app.route('/api/news-data')
def get_news_data():
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        article = data['data'][0]
        
        words = article['title'].split(' ')
        green_indices = get_random_word_indices(words, 3)
        
        return jsonify({
            'title': article['title'],
            'image_url': article['image_url'],
            'green_word_indices': green_indices
        })
        
    except Exception as e:
        print(f'Error fetching news: {str(e)}')
        return jsonify({'error': 'Failed to fetch news', 'message': str(e)}), 500

@app.route('/')
def index():
    """Main page - Shows HTML interface with live status"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>News Bot - Auto Instagram Poster</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .status-box {
            background: #f7f7f7;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            min-height: 300px;
            max-height: 400px;
            overflow-y: auto;
        }
        .status-item {
            padding: 10px;
            margin: 5px 0;
            border-radius: 6px;
            font-size: 14px;
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .status-item.info { background: #e3f2fd; color: #1565c0; }
        .status-item.success { background: #e8f5e9; color: #2e7d32; }
        .status-item.error { background: #ffebee; color: #c62828; }
        .status-item.warning { background: #fff3e0; color: #e65100; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 12px;
            display: none;
        }
        .result.show { display: block; }
        .result.success { background: #e8f5e9; border-left: 4px solid #2e7d32; }
        .result.error { background: #ffebee; border-left: 4px solid #c62828; }
        .result h3 { margin-bottom: 10px; }
        .result p { font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📰 News Bot</h1>
        <p class="subtitle">Automated Instagram News Poster</p>
        
        <div class="status-box" id="statusBox">
            <div class="status-item info">⌛ Ready to fetch and post news...</div>
        </div>
        
        <button class="btn" id="startBtn" onclick="startPosting()">
            <span id="btnText">🚀 Start Posting</span>
        </button>
        
        <div class="result" id="result"></div>
    </div>
    
    <script>
        function addStatus(message, type = 'info') {
            const statusBox = document.getElementById('statusBox');
            const item = document.createElement('div');
            item.className = `status-item ${type}`;
            item.textContent = message;
            statusBox.appendChild(item);
            statusBox.scrollTop = statusBox.scrollHeight;
        }
        
        async function startPosting() {
            const btn = document.getElementById('startBtn');
            const btnText = document.getElementById('btnText');
            const resultBox = document.getElementById('result');
            const statusBox = document.getElementById('statusBox');
            
            // Reset
            btn.disabled = true;
            btnText.innerHTML = '<span class="spinner"></span> Processing...';
            resultBox.className = 'result';
            statusBox.innerHTML = '';
            
            try {
                addStatus('🚀 Starting process...', 'info');
                
                const response = await fetch('/api/process-and-post');
                const data = await response.json();
                
                // Show all status messages
                if (data.status) {
                    data.status.forEach(msg => {
                        let type = 'info';
                        if (msg.includes('✅')) type = 'success';
                        else if (msg.includes('❌')) type = 'error';
                        else if (msg.includes('⚠')) type = 'warning';
                        addStatus(msg, type);
                    });
                }
                
                // Show final result
                resultBox.className = `result show ${data.success ? 'success' : 'error'}`;
                if (data.success) {
                    resultBox.innerHTML = `
                        <h3>✅ Successfully Posted!</h3>
                        <p><strong>Title:</strong> ${data.title}</p>
                        <p><strong>Category:</strong> ${data.category}</p>
                        <p><strong>Post ID:</strong> ${data.post_id}</p>
                    `;
                } else {
                    resultBox.innerHTML = `
                        <h3>❌ ${data.error || 'Failed'}</h3>
                        <p>${data.message || data.details || 'Unknown error'}</p>
                    `;
                }
            } catch (error) {
                addStatus(`❌ Network Error: ${error.message}`, 'error');
                resultBox.className = 'result show error';
                resultBox.innerHTML = `<h3>❌ Connection Failed</h3><p>${error.message}</p>`;
            } finally {
                btn.disabled = false;
                btnText.textContent = '🔄 Post Another';
            }
        }
    </script>
</body>
</html>
    '''

@app.route('/api/process-and-post')
def process_and_post():
    """Main endpoint - Auto fetch, generate, and post to Instagram with status display"""
    try:
        status_messages = []
        
        # Step 1: Check if credentials are configured
        status_messages.append('🔍 Checking credentials...')
        if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
            return jsonify({
                'success': False,
                'error': 'Instagram credentials not configured',
                'message': 'Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID',
                'setup_guide': request.host_url.rstrip('/') + '/get-token',
                'status': status_messages
            }), 400
        status_messages.append('✅ Credentials OK')
        
        # Step 2: Fetch news
        status_messages.append('📰 Fetching latest news...')
        print('📰 Fetching latest news...')
        response = requests.get(API_URL, timeout=10)
        news_data = response.json()
        
        if 'error' in news_data:
            status_messages.append(f'❌ News API Error: {news_data["error"].get("message", "Unknown error")}')
            return jsonify({
                'success': False,
                'error': 'News API Error',
                'message': news_data['error'].get('message', 'Failed to fetch news'),
                'status': status_messages
            }), 500
        
        status_messages.append(f'✅ Found {len(news_data.get("data", []))} news articles')
        
        # Step 3: Find first unposted news
        status_messages.append('🔍 Checking for unposted news...')
        print('🔍 Checking for unposted news...')
        article = None
        for item in news_data['data']:
            news_id = item.get('uuid', item.get('url', ''))
            if not is_news_posted(news_id):
                article = item
                break
        
        if not article:
            status_messages.append('ℹ️ All news already posted')
            return jsonify({
                'success': False,
                'message': 'All recent news have already been posted',
                'posted_count': len(load_posted_news()),
                'status': status_messages
            }), 200
        
        # Step 4: Extract article data
        news_id = article.get('uuid', article.get('url', ''))
        category = article.get('categories', ['News'])[0] if article.get('categories') else 'News'
        source = article.get('source', 'Unknown')
        description = article.get('description', '') or article.get('snippet', '')
        title = article['title']
        
        status_messages.append(f'📌 Selected: {title[:50]}...')
        print(f'📌 Selected: {title[:50]}...')
        
        # Step 5: Generate image URL
        status_messages.append('🎨 Generating news card image...')
        base_url = request.host_url.rstrip('/')
        image_url = f"{base_url}/api/news-card"
        status_messages.append('✅ Image URL ready')
        
        # Step 6: Generate caption
        status_messages.append('✍️ Creating caption...')
        caption_parts = [
            f"📰 {title}",
            "",
            f"📝 {description[:150]}..." if description else "",
            "",
            f"📌 Source: {source}",
            f"🏷️ Category: {category}",
            "",
            f"#news #breaking #updates #{category.lower().replace(' ', '')}",
            "",
            f"[ID:{news_id[:20]}]"  # Hidden identifier for duplicate detection
        ]
        caption = "\n".join([p for p in caption_parts if p])
        status_messages.append('✅ Caption generated')
        
        status_messages.append('📸 Uploading to Instagram...')
        print('📸 Uploading to Instagram...')
        
        # Step 7: Post to Instagram (skip URL check to avoid circular requests)
        result = upload_image_to_instagram(image_url, caption, skip_url_check=True)
        
        if result['success']:
            # Step 8: Mark as posted
            status_messages.append('💾 Saving post record...')
            save_posted_news(news_id)
            print('✅ Successfully posted!')
            status_messages.append('🎉 Successfully posted to Instagram!')
            
            return jsonify({
                'success': True,
                'message': '🎉 Successfully posted to Instagram!',
                'post_id': result['post_id'],
                'title': title,
                'category': category,
                'source': source,
                'image_url': image_url,
                'caption': caption,
                'status': status_messages
            })
        else:
            status_messages.append(f'❌ Instagram error: {result.get("error")}')
            return jsonify({
                'success': False,
                'error': result.get('error'),
                'details': result.get('details'),
                'title': title,
                'status': status_messages
            }), 500
            
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        status_messages.append(f'❌ Error: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to process request',
            'message': str(e),
            'status': status_messages
        }), 500

@app.route('/debug/fonts')
def debug_fonts():
    """Debug endpoint to check font availability"""
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # List all files in directory
    try:
        files = os.listdir(script_dir)
    except:
        files = ['ERROR: Cannot list directory']
    
    # Check specific font files
    title_font_path = os.path.join(script_dir, 'Roboto-Bold.ttf')
    category_font_path = os.path.join(script_dir, 'Roboto-Regular.ttf')
    
    return jsonify({
        'script_directory': script_dir,
        'directory_contents': files[:50],
        'roboto_bold_exists': os.path.exists(title_font_path),
        'roboto_regular_exists': os.path.exists(category_font_path),
        'title_font_path': title_font_path,
        'category_font_path': category_font_path
    })

@app.route('/health')
def health():
    """Health check endpoint with configuration info"""
    config = load_config()
    return jsonify({
        'status': 'OK',
        'message': 'News Card API is running',
        'config_source': 'config.json' if os.path.exists(CONFIG_FILE) else 'defaults',
        'apis_configured': {
            'news_api': bool(config.get('news_api_url')),
            'instagram': bool(config.get('instagram_access_token') and config.get('instagram_account_id'))
        }
    })

# Instagram Posting Functions
def upload_image_to_instagram(image_url, caption, skip_url_check=False):
    """Upload image to Instagram and publish"""
    try:
        # Skip URL check for localhost or if explicitly requested
        if not skip_url_check and 'localhost' not in image_url and '127.0.0.1' not in image_url:
            print(f'Testing if image URL is accessible: {image_url}')
            try:
                test_response = requests.head(image_url, timeout=5)
                print(f'Image URL status code: {test_response.status_code}')
                if test_response.status_code != 200:
                    return {
                        'success': False, 
                        'error': f'Image URL returned status {test_response.status_code}',
                        'details': 'The image URL must be publicly accessible and return 200 OK'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'error': 'Image URL is not accessible',
                    'details': f'Could not reach image URL: {str(e)}'
                }
        
        # Step 1: Create media container
        container_url = f"https://graph.facebook.com/v24.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        container_data_payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        print(f'Creating Instagram media container...')
        container_response = requests.post(container_url, data=container_data_payload)
        container_data = container_response.json()
        
        print(f'Instagram API response: {container_data}')
        
        if 'id' not in container_data:
            error_message = container_data.get('error', {}).get('message', 'Unknown error')
            return {'success': False, 'error': 'Failed to create media container', 'details': error_message, 'full_response': container_data}
        
        creation_id = container_data['id']
        print(f'Media container created: {creation_id}')
        
        # Step 2: Wait for container to be ready
        print('Waiting for media to process...')
        time.sleep(5)
        
        # Step 3: Publish the media
        publish_url = f"https://graph.facebook.com/v24.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
        publish_data_payload = {
            'creation_id': creation_id,
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        print('Publishing to Instagram...')
        publish_response = requests.post(publish_url, data=publish_data_payload)
        publish_data = publish_response.json()
        
        if 'id' not in publish_data:
            return {'success': False, 'error': 'Failed to publish', 'details': publish_data}
        
        print(f'Successfully posted to Instagram: {publish_data["id"]}')
        return {'success': True, 'post_id': publish_data['id']}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/api/post-to-instagram', methods=['POST'])
def post_to_instagram():
    """Generate news card and post to Instagram with duplicate prevention"""
    try:
        # Step 1: Check if credentials are configured
        print('Step 1: Checking Instagram credentials...')
        if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
            return jsonify({
                'success': False,
                'error': 'Instagram credentials not configured',
                'message': 'Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID environment variables'
            }), 400
        
        time.sleep(0.3)
        
        # Step 2: Fetch news
        print('Step 2: Fetching news for Instagram post...')
        response = requests.get(API_URL, timeout=10)
        news_data = response.json()
        
        # Step 3: Find first unposted news
        print('Step 3: Finding unposted news...')
        article = None
        for item in news_data['data']:
            news_id = item.get('uuid', item.get('url', ''))
            if not is_news_posted(news_id):
                article = item
                print(f'Found unposted news: {article["title"][:50]}...')
                break
        
        if not article:
            return jsonify({
                'success': False,
                'error': 'No new news to post',
                'message': 'All recent news have already been posted'
            }), 400
        
        time.sleep(0.5)
        
        # Step 4: Extract article data
        print('Step 4: Extracting article data...')
        news_id = article.get('uuid', article.get('url', ''))
        category = article.get('categories', ['News'])[0] if article.get('categories') else 'News'
        source = article.get('source', 'Unknown')
        # Use description if available, otherwise use snippet
        description = article.get('description', '') or article.get('snippet', '')
        title = article['title']
        
        # Step 5: Generate caption
        print('Step 5: Generating caption...')
        # Get custom caption from request body (optional)
        data = request.get_json() or {}
        custom_caption = data.get('caption', '')
        
        if custom_caption:
            caption = custom_caption
        else:
            # Auto-generate caption with title, description, source, and category
            caption_parts = [
                f"📰 {title}",
                "",
                f"📝 {description[:150]}..." if description else "",
                "",
                f"📌 Source: {source}",
                f"🏷️ Category: {category}",
                "",
                "#news #breaking #updates #" + category.lower().replace(' ', '')
            ]
            caption = "\n".join([p for p in caption_parts if p])
        
        print(f'Caption preview: {caption[:100]}...')
        time.sleep(0.5)
        
        # Step 6: Get publicly accessible image URL
        print('Step 6: Preparing image URL...')
        base_url = request.host_url.rstrip('/')
        
        # Check if running on localhost
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            return jsonify({
                'success': False,
                'error': 'Cannot post from localhost',
                'message': 'Instagram requires a publicly accessible HTTPS URL. Please deploy to Vercel or use ngrok for local testing.',
                'solutions': [
                    '1. Deploy to Vercel: vercel --prod',
                    '2. Use ngrok: ngrok http 3000',
                    '3. Update the image URL to point to your deployed instance'
                ]
            }), 400
        
        image_url = f"{base_url}/api/news-card"
        
        print(f'Using image URL: {image_url}')
        time.sleep(0.3)
        
        # Step 7: Post to Instagram
        print('Step 7: Posting to Instagram...')
        result = upload_image_to_instagram(image_url, caption)
        
        if result['success']:
            # Step 8: Mark news as posted
            print('Step 8: Marking news as posted...')
            save_posted_news(news_id)
            time.sleep(0.2)
            
            print('✅ Successfully posted to Instagram!')
            return jsonify({
                'success': True,
                'message': 'Successfully posted to Instagram',
                'post_id': result['post_id'],
                'news_id': news_id,
                'title': title,
                'category': category,
                'source': source,
                'caption': caption,
                'image_url': image_url
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error'),
                'details': result.get('details')
            }), 500
            
    except Exception as e:
        print(f'Error posting to Instagram: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Failed to post to Instagram',
            'message': str(e)
        }), 500

@app.route('/api/instagram/status')
def instagram_status():
    """Check Instagram API configuration status"""
    return jsonify({
        'configured': bool(INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID),
        'has_access_token': bool(INSTAGRAM_ACCESS_TOKEN),
        'has_account_id': bool(INSTAGRAM_BUSINESS_ACCOUNT_ID)
    })

@app.route('/api/instagram/find-account', methods=['POST'])
def find_instagram_account():
    """Find Instagram Business Account ID from access token"""
    try:
        data = request.get_json() or {}
        access_token = data.get('access_token', '').strip() or INSTAGRAM_ACCESS_TOKEN
        
        if not access_token:
            return jsonify({
                'success': False,
                'error': 'Access token required'
            }), 400
        
        # Step 1: Get Facebook Pages associated with the token
        pages_url = "https://graph.facebook.com/v24.0/me/accounts"
        pages_params = {
            'access_token': access_token,
            'fields': 'id,name,access_token'
        }
        
        pages_response = requests.get(pages_url, params=pages_params)
        pages_data = pages_response.json()
        
        if 'error' in pages_data:
            return jsonify({
                'success': False,
                'error': 'Failed to get Facebook Pages',
                'details': pages_data['error'],
                'message': 'Make sure your access token has pages_show_list permission'
            }), 400
        
        if 'data' not in pages_data or len(pages_data['data']) == 0:
            return jsonify({
                'success': False,
                'error': 'No Facebook Pages found',
                'message': 'You need to have a Facebook Page connected to your Instagram Business Account'
            }), 400
        
        # Step 2: Find Instagram accounts for each page
        instagram_accounts = []
        for page in pages_data['data']:
            page_id = page['id']
            page_name = page['name']
            page_token = page.get('access_token', access_token)
            
            # Get Instagram account connected to this page
            ig_url = f"https://graph.facebook.com/v24.0/{page_id}"
            ig_params = {
                'access_token': page_token,
                'fields': 'instagram_business_account'
            }
            
            ig_response = requests.get(ig_url, params=ig_params)
            ig_data = ig_response.json()
            
            if 'instagram_business_account' in ig_data:
                ig_account_id = ig_data['instagram_business_account']['id']
                
                # Get Instagram account details
                ig_details_url = f"https://graph.facebook.com/v24.0/{ig_account_id}"
                ig_details_params = {
                    'access_token': page_token,
                    'fields': 'id,username,name,profile_picture_url'
                }
                
                ig_details_response = requests.get(ig_details_url, params=ig_details_params)
                ig_details = ig_details_response.json()
                
                instagram_accounts.append({
                    'instagram_account_id': ig_account_id,
                    'instagram_username': ig_details.get('username', 'Unknown'),
                    'instagram_name': ig_details.get('name', 'Unknown'),
                    'facebook_page_id': page_id,
                    'facebook_page_name': page_name,
                    'profile_picture': ig_details.get('profile_picture_url', '')
                })
        
        if len(instagram_accounts) == 0:
            return jsonify({
                'success': False,
                'error': 'No Instagram Business Accounts found',
                'message': 'None of your Facebook Pages are connected to an Instagram Business Account',
                'pages_found': [{'id': p['id'], 'name': p['name']} for p in pages_data['data']],
                'help': 'Go to your Facebook Page Settings > Instagram > Connect Account'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'Found {len(instagram_accounts)} Instagram Business Account(s)',
            'accounts': instagram_accounts,
            'note': 'Use the instagram_account_id value in your configuration'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/instagram/test', methods=['POST'])
def test_instagram_api():
    """Test Instagram API with detailed error information"""
    try:
        if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_ACCOUNT_ID:
            return jsonify({
                'success': False,
                'error': 'Credentials not configured'
            }), 400
        
        # Test 1: Verify access token is valid
        test_url = f"https://graph.facebook.com/v24.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}"
        test_params = {'access_token': INSTAGRAM_ACCESS_TOKEN, 'fields': 'id,username'}
        
        response = requests.get(test_url, params=test_params)
        result = response.json()
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': 'Instagram API Error',
                'details': result['error'],
                'message': 'Your access token or account ID might be invalid or expired'
            }), 400
        
        # Test 2: Try creating a test media container with the actual image URL
        base_url = request.host_url.rstrip('/')
        image_url = f"{base_url}/api/news-card"
        
        container_url = f"https://graph.facebook.com/v24.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        container_payload = {
            'image_url': image_url,
            'caption': 'Test post from News Bot API',
            'access_token': INSTAGRAM_ACCESS_TOKEN
        }
        
        container_response = requests.post(container_url, data=container_payload)
        container_data = container_response.json()
        
        if 'error' in container_data:
            return jsonify({
                'success': False,
                'step': 'create_container',
                'error': container_data['error'],
                'image_url': image_url,
                'message': 'Failed to create media container'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Instagram API is working correctly',
            'account_info': result,
            'container_id': container_data.get('id'),
            'image_url': image_url,
            'note': 'Container created but not published (test only)'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Admin Panel Endpoints
@app.route('/admin')
def admin_panel():
    """Serve admin panel"""
    return send_file('admin.html')

@app.route('/privacy')
def privacy_policy():
    """Serve privacy policy"""
    return send_file('privacy.html')

@app.route('/get-token')
def get_token_guide():
    """Serve access token setup guide"""
    return send_file('get-token.html')

@app.route('/api/admin/config', methods=['GET'])
def get_admin_config():
    """Get current configuration (without sensitive data)"""
    try:
        config = load_config()
        return jsonify({
            'success': True,
            'config': {
                'news_api_url': config.get('news_api_url', ''),
                'instagram_configured': bool(config.get('instagram_access_token') and config.get('instagram_account_id'))
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/update-news-api', methods=['POST'])
def update_news_api():
    """Update News API URL"""
    try:
        data = request.get_json()
        api_url = data.get('api_url', '').strip()
        
        if not api_url:
            return jsonify({'success': False, 'error': 'API URL is required'}), 400
        
        # Load current config
        config = load_config()
        config['news_api_url'] = api_url
        saved = save_config(config)
        
        # Update global variable
        global API_URL
        API_URL = api_url
        
        if not saved:
            return jsonify({
                'success': True,
                'message': 'News API URL updated in memory (Vercel serverless mode)',
                'warning': 'Changes will be lost on next deployment.',
                'note': 'Config saved temporarily for this session only'
            })
        
        return jsonify({'success': True, 'message': 'News API URL updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/update-instagram', methods=['POST'])
def update_instagram():
    """Update Instagram API credentials"""
    try:
        data = request.get_json()
        access_token = data.get('access_token', '').strip()
        account_id = data.get('account_id', '').strip()
        
        if not access_token or not account_id:
            return jsonify({'success': False, 'error': 'Both access token and account ID are required'}), 400
        
        # Load current config
        config = load_config()
        config['instagram_access_token'] = access_token
        config['instagram_account_id'] = account_id
        saved = save_config(config)
        
        # Update global variables
        global INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID
        INSTAGRAM_ACCESS_TOKEN = access_token
        INSTAGRAM_BUSINESS_ACCOUNT_ID = account_id
        
        if not saved:
            return jsonify({
                'success': True,
                'message': 'Instagram credentials updated in memory (Vercel serverless mode)',
                'warning': 'Changes will be lost on next deployment. Set environment variables in Vercel dashboard for persistence.',
                'note': 'Go to Vercel Dashboard > Settings > Environment Variables'
            })
        
        return jsonify({'success': True, 'message': 'Instagram credentials updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/clear-history', methods=['POST'])
def clear_posted_history():
    """Clear posted news history"""
    try:
        if os.path.exists(POSTED_NEWS_FILE):
            os.remove(POSTED_NEWS_FILE)
        return jsonify({'success': True, 'message': 'Posted news history cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print('🚀 News Card API running on http://localhost:3000')
    print('📸 Generate card: http://localhost:3000/api/news-card')
    print('📰 Get news data: http://localhost:3000/api/news-data')
    print('⚙️  Admin Panel: http://localhost:3000/admin')
    app.run(host='0.0.0.0', port=3000, debug=False)

# For Vercel serverless deployment
# The app object is automatically picked up by Vercel

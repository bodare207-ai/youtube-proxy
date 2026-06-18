"""
YouTube Proxy Server - Deploy on Render/Railway
This server acts as a bridge between your offline YouTube and real YouTube
"""

from flask import Flask, request, jsonify, Response
import yt_dlp
import requests
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins

# ==================== VIDEO INFO ====================
@app.route('/api/info')
def get_video_info():
    """Get video metadata (title, thumbnail, duration, etc.)"""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'id': info.get('id'),
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'channel': info.get('channel'),
                'channel_id': info.get('channel_id'),
                'description': info.get('description', '')[:500],
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'upload_date': info.get('upload_date'),
                'categories': info.get('categories', []),
                'tags': info.get('tags', [])[:10],
                'is_live': info.get('is_live', False),
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== VIDEO STREAMING ====================
@app.route('/api/stream')
def stream_video():
    """Stream video directly from YouTube (no download)"""
    url = request.args.get('url')
    format_id = request.args.get('format_id', 'best')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': format_id,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url')
            
            if not video_url and info.get('formats'):
                for f in info.get('formats', []):
                    if f.get('format_id') == format_id or format_id == 'best':
                        video_url = f.get('url')
                        break
            
            if not video_url:
                return jsonify({'error': 'No video URL found'}), 404
            
            # Stream the video
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Range': request.headers.get('Range', 'bytes=0-'),
            }
            
            response = requests.get(video_url, headers=headers, stream=True)
            
            return Response(
                response.iter_content(chunk_size=8192),
                status=response.status_code,
                headers={
                    'Content-Type': response.headers.get('Content-Type', 'video/mp4'),
                    'Content-Length': response.headers.get('Content-Length'),
                    'Accept-Ranges': 'bytes',
                    'Cache-Control': 'public, max-age=31536000',
                }
            )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== SEARCH ====================
@app.route('/api/search')
def search_videos():
    """Search YouTube videos"""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))
    
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'ytsearch{limit}:{query}', download=False)
            results = []
            for entry in info.get('entries', []):
                results.append({
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'duration': entry.get('duration'),
                    'thumbnail': entry.get('thumbnail'),
                    'channel': entry.get('channel'),
                    'channel_id': entry.get('channel_id'),
                    'view_count': entry.get('view_count'),
                    'upload_date': entry.get('upload_date'),
                    'url': entry.get('webpage_url'),
                })
            return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== HEALTH CHECK ====================
@app.route('/')
def health():
    return jsonify({
        'status': 'online',
        'version': '1.0',
        'message': 'YouTube Proxy Server is running!'
    })

@app.route('/ping')
def ping():
    return 'pong'

# ==================== MAIN ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

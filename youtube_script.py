from flask import Flask, request, jsonify, Response
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

import re
import json

app = Flask(__name__)
app.config['ensure_ascii'] = False  # This ensures Unicode characters are not escaped

def get_video_id(url):
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    - youtube.com/v/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    - m.youtube.com variations
    - URLs with additional parameters
    
    Args:
        url (str): YouTube URL
        
    Returns:
        str or None: 11-character video ID if found, None otherwise
    """
    if not url or not isinstance(url, str):
        return None
    
    # Comprehensive regex pattern for all YouTube URL formats
    patterns = [
        # Standard watch URLs: youtube.com/watch?v=VIDEO_ID
        r'(?:youtube\.com|m\.youtube\.com)\/watch\?.*v=([a-zA-Z0-9_-]{11})',
        # Short URLs: youtu.be/VIDEO_ID
        r'youtu\.be\/([a-zA-Z0-9_-]{11})',
        # Embed URLs: youtube.com/embed/VIDEO_ID
        r'(?:youtube\.com|m\.youtube\.com)\/embed\/([a-zA-Z0-9_-]{11})',
        # Direct video URLs: youtube.com/v/VIDEO_ID
        r'(?:youtube\.com|m\.youtube\.com)\/v\/([a-zA-Z0-9_-]{11})',
        # YouTube Shorts: youtube.com/shorts/VIDEO_ID
        r'(?:youtube\.com|m\.youtube\.com)\/shorts\/([a-zA-Z0-9_-]{11})',
        # Live URLs: youtube.com/live/VIDEO_ID
        r'(?:youtube\.com|m\.youtube\.com)\/live\/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

@app.route('/transcript', methods=['GET'])
def transcript():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({'error': 'Missing url parameter'}), 400
    video_id = get_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    try:
        ytt_api = YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username="mmsjqszc",proxy_password="fy3ur75y5y15",
            )
        )
        transcript =  ytt_api.fetch(video_id, languages=['de', 'en'])
        script = ''
        for snippet in transcript:
          script+=(' ' +snippet.text)
        print(script)
        # Use custom JSON response to preserve German characters
        response_data = {'transcript': script}
        json_response = json.dumps(response_data, ensure_ascii=False, indent=2)
        return Response(
            json_response,
            content_type='application/json; charset=utf-8'
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        error_response = json.dumps({'error': str(e)}, ensure_ascii=False)
        return Response(
            error_response,
            content_type='application/json; charset=utf-8',
            status=500
        )

if __name__ == '__main__':
    app.run(debug=True)



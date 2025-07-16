from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

import re

app = Flask(__name__)

def get_video_id(url):
    match = re.search(r"[?&]v=([\w-]{11})", url)
    if match:
        return match.group(1)
    match = re.search(r"youtu\.be/([\w-]{11})", url)
    if match:
        return match.group(1)
    match = re.search(r"youtube\.com/embed/([\w-]{11})", url)
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
        transcript =  ytt_api.fetch(video_id)
        script = ''
        for snippet in transcript:
          script+=snippet.text
        return jsonify({'transcript': script})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)



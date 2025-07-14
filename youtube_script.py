from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
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
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        script = " ".join([entry['text'] for entry in transcript])
        return jsonify({'transcript': script})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, request, jsonify, Response
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig

import re
import json
import string

app = Flask(__name__)
app.config['ensure_ascii'] = False  # This ensures Unicode characters are not escaped
app.config['TRANSLATION_ENABLED'] = False
app.config['TRANSLATION_LANGUAGE'] = 'en'

SETTINGS_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>YouTube Extraction Settings</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; max-width: 560px; }
    h1 { margin-bottom: 8px; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; }
    label { display: block; margin-bottom: 8px; }
    button { margin-top: 12px; padding: 8px 14px; cursor: pointer; }
    .hint { color: #555; font-size: 14px; margin-top: 6px; }
  </style>
</head>
<body>
  <h1>YouTube Extraction Settings</h1>
  <div class="card">
    <label>
      <input id="translationToggle" type="checkbox">
      Enable translation
    </label>
    <div class="hint">When disabled, transcripts stay in the video's original language.</div>
    <button id="saveBtn">Save</button>
    <p id="status"></p>
  </div>

  <script>
    async function loadSettings() {
      const response = await fetch('/settings/data');
      const data = await response.json();
      document.getElementById('translationToggle').checked = !!data.translation_enabled;
    }

    async function saveSettings() {
      const enabled = document.getElementById('translationToggle').checked;
      const response = await fetch('/settings/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ translation_enabled: enabled })
      });
      const data = await response.json();
      const status = document.getElementById('status');
      status.textContent = data.message || 'Saved';
    }

    document.getElementById('saveBtn').addEventListener('click', saveSettings);
    loadSettings();
  </script>
</body>
</html>
"""

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


def parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def normalize_transcript_text(text):
    compact = ' '.join(text.strip().split())
    no_punctuation = compact.translate(str.maketrans('', '', string.punctuation))
    return no_punctuation.lower().strip()


def remove_prefix_overlap(previous_text, current_text, minimum_overlap_words=3):
    prev_words = previous_text.split()
    current_words = current_text.split()
    max_overlap = min(len(prev_words), len(current_words))

    for overlap_size in range(max_overlap, minimum_overlap_words - 1, -1):
        if prev_words[-overlap_size:] == current_words[:overlap_size]:
            return ' '.join(current_words[overlap_size:]).strip()

    return current_text


def build_script_from_transcript(transcript):
    script_parts = []
    previous_normalized = None
    previous_text = ''
    recent_normalized_snippets = []

    for snippet in transcript:
        current_text = snippet.text.strip()
        if not current_text:
            continue

        original_normalized = normalize_transcript_text(current_text)
        normalized_current = original_normalized
        if normalized_current in recent_normalized_snippets:
            continue
        if normalized_current == previous_normalized:
            continue

        if previous_text:
            current_text = remove_prefix_overlap(previous_text, current_text)
            if not current_text:
                continue
            normalized_current = normalize_transcript_text(current_text)
            if normalized_current == previous_normalized:
                continue

        script_parts.append(current_text)
        previous_text = current_text
        previous_normalized = normalized_current
        recent_normalized_snippets.append(original_normalized)
        recent_normalized_snippets.append(normalized_current)
        if len(recent_normalized_snippets) > 4:
            recent_normalized_snippets.pop(0)

    return ' '.join(script_parts)


@app.route('/settings', methods=['GET'])
def settings_page():
    return Response(SETTINGS_HTML, content_type='text/html; charset=utf-8')


@app.route('/settings/data', methods=['GET', 'POST'])
def settings_data():
    if request.method == 'GET':
        return jsonify({
            'translation_enabled': app.config['TRANSLATION_ENABLED'],
            'translation_language': app.config['TRANSLATION_LANGUAGE']
        })

    payload = request.get_json(silent=True) or {}
    app.config['TRANSLATION_ENABLED'] = parse_bool(
        payload.get('translation_enabled'),
        app.config['TRANSLATION_ENABLED']
    )
    language = payload.get('translation_language')
    if isinstance(language, str) and language.strip():
        app.config['TRANSLATION_LANGUAGE'] = language.strip().lower()

    return jsonify({
        'message': 'Settings saved',
        'translation_enabled': app.config['TRANSLATION_ENABLED'],
        'translation_language': app.config['TRANSLATION_LANGUAGE']
    })

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
        translate_override = request.args.get('translate')
        translation_enabled = parse_bool(
            translate_override,
            app.config['TRANSLATION_ENABLED']
        )

        if translation_enabled:
            target_language = request.args.get(
                'translation_language',
                app.config['TRANSLATION_LANGUAGE']
            )
            transcript = ytt_api.fetch(video_id, languages=[target_language])
        else:
            transcript = ytt_api.fetch(video_id)

        script = build_script_from_transcript(transcript)
        print(script)
        response_data = {
            'transcript': script,
            'translation_enabled': translation_enabled
        }
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

import base64
import requests
from config import ELEVENLABS_API_KEY
from viseme_utils import viseme_mapper

def generate_audio_base64(text, voice_id="21m00Tcm4TlvDq8ikWAM"):
    """
    Generate audio from text using ElevenLabs API.
    Returns base64 encoded audio data.
    """
    if not ELEVENLABS_API_KEY:
        print("⚠️ ElevenLabs API key not configured. Skipping audio generation.")
        return None
    
    TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(TTS_URL, json=data, headers=headers)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')
    except requests.exceptions.RequestException as e:
        print(f"Error during ElevenLabs API call: {e}")
        return None

def generate_audio_with_visemes(text, voice_id="21m00Tcm4TlvDq8ikWAM"):
    """
    Generate audio from text with viseme timing information.
    Returns dict with audio data and viseme timeline.
    """
    audio_b64 = generate_audio_base64(text, voice_id)
    
    if not audio_b64:
        return None
    
    # Estimate audio duration (rough approximation: ~150 words per minute)
    words = len(text.split())
    estimated_duration = (words / 150.0) * 60.0  # Convert to seconds
    
    # Generate viseme timeline
    viseme_frames = viseme_mapper.create_viseme_timeline(text, estimated_duration)
    
    return {
        'audio': audio_b64,
        'viseme_frames': [
            {
                'viseme_id': frame.viseme_id,
                'viseme_name': frame.viseme_name,
                'image_path': frame.image_path,
                'start_time': frame.start_time,
                'duration': frame.duration,
                'intensity': frame.intensity
            }
            for frame in viseme_frames
        ],
        'estimated_duration': estimated_duration
    }

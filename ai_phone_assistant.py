# ai_phone_assistant.py

from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
import requests
import base64
import os

app = Flask(__name__)

# === Configuration ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID") or "yr43K8H5LoTp6S1QFSGg" # fallback if not set

def transcribe_audio(audio_url):
    import openai
    openai.api_key = OPENAI_API_KEY

    audio_data = requests.get(audio_url).content
    with open("caller_input.mp3", "wb") as f:
        f.write(audio_data)

    with open("caller_input.mp3", "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript['text']

def generate_response(text):
    import openai
    openai.api_key = OPENAI_API_KEY

    messages = [
        {"role": "system", "content": "You are a helpful AI receptionist."},
        {"role": "user", "content": text}
    ]
    res = openai.ChatCompletion.create(model="gpt-4", messages=messages)
    return res.choices[0].message.content

def synthesize_speech(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    response = requests.post(url, headers=headers, json=data)
    audio_path = os.path.join("static", "response.mp3")
    with open(audio_path, "wb") as f:
        f.write(response.content)
    return audio_path

@app.route("/voice", methods=['POST'])
def voice():
    resp = VoiceResponse()
    gather = Gather(input='speech', action='/process', timeout=5)
    gather.say("Hello! How can I help you today?")
    resp.append(gather)
    resp.redirect('/voice')
    return Response(str(resp), mimetype='text/xml')

@app.route("/process", methods=['POST'])
def process():
    recording_url = request.form.get('RecordingUrl')
    if not recording_url:
        speech_text = request.form.get('SpeechResult', '')
    else:
        speech_text = transcribe_audio(recording_url)

    print("Caller said:", speech_text)
    reply = generate_response(speech_text)
    print("AI replied:", reply)

    speech_file = synthesize_speech(reply)
    # Make sure your server hosts /static/ folder publicly, adjust your-domain.com accordingly
    speech_url = f"https://your-domain.com/static/response.mp3"

    resp = VoiceResponse()
    resp.play(speech_url)
    resp.redirect('/voice')  # Loop the conversation
    return Response(str(resp), mimetype='text/xml')

if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(debug=True, port=5000)

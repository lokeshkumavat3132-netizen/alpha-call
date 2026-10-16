import os
import tempfile
import threading
import time
import requests
import edge_tts
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from groq import Groq

OWNER_NAME = "Lokesh"
DEFAULT_PHONE_NUMBER = "+917977804035"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
NTFY_TOPIC = "alpha_call_917977804035"
VOICE_NAME = "hi-IN-MadhurNeural"

client = Groq(api_key=GROQ_API_KEY)
app = FastAPI()

incoming_ring_state = {"ringing": False, "reason": ""}

conversation_memory = [
    {
        "role": "system",
        "content": (
            f"You are Alpha, a sharp, loyal, JARVIS-like AI assistant created by {OWNER_NAME}. "
            f"Your Boss {OWNER_NAME}'s mobile number is {DEFAULT_PHONE_NUMBER}. "
            "You are running 24/7 on the cloud and talking to him on a live voice call. "
            "Keep replies natural, witty, and concise (1 to 2 sentences max) in Hinglish."
        )
    }
]

@app.get("/", response_class=HTMLResponse)
async def call_screen():
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>Alpha Native Call</title>
    <style>
        body {{
            margin: 0; background: #000; color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; flex-direction: column; align-items: center; justify-content: space-between;
            height: 100vh; padding: 50px 20px 40px 20px; box-sizing: border-box; overflow: hidden;
        }}
        .caller-info {{ text-align: center; margin-top: 20px; }}
        .app-name {{ font-size: 14px; text-transform: uppercase; letter-spacing: 3px; color: #8e8e93; }}
        .caller-id {{ font-size: 38px; font-weight: 600; margin-top: 10px; color: #fff; }}
        .call-status {{ font-size: 16px; color: #00e676; margin-top: 8px; font-weight: 400; }}
        
        .visualizer {{
            width: 120px; height: 120px; border-radius: 50%;
            background: radial-gradient(circle, #00e676 0%, #004d40 70%, transparent 100%);
            box-shadow: 0 0 50px #00e67666; display: flex; align-items: center; justify-content: center;
            animation: pulseRing 1.5s infinite;
        }}
        @keyframes pulseRing {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.7); }}
            70% {{ transform: scale(1.05); box-shadow: 0 0 0 25px rgba(0, 230, 118, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 230, 118, 0); }}
        }}
        .visualizer.speaking {{
            background: radial-gradient(circle, #00f0ff 0%, #0022ff 70%, transparent 100%);
            box-shadow: 0 0 60px #00f0ff88;
        }}
        
        .transcript {{
            text-align: center; font-size: 15px; color: #d1d1d6;
            min-height: 50px; max-width: 90%; line-height: 1.4;
        }}
        
        .action-tray {{ display: flex; width: 100%; justify-content: space-around; max-width: 320px; margin-bottom: 20px; }}
        .call-btn {{
            width: 75px; height: 75px; border-radius: 50%; border: none;
            display: flex; align-items: center; justify-content: center; cursor: pointer;
            font-size: 16px; font-weight: 600; color: #fff; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }}
        .btn-accept {{ background: #34c759; }}
        .btn-decline {{ background: #ff3b30; }}
        .btn-speak {{ background: #007aff; width: 100%; border-radius: 40px; height: 60px; font-size: 17px; }}
    </style>
</head>
<body>
    <div class="caller-info">
        <div class="app-name">Alpha Audio Call</div>
        <div class="caller-id">ALPHA AI</div>
        <div class="call-status" id="status">Incoming Secure Line...</div>
    </div>

    <div class="visualizer" id="orb"></div>

    <div class="transcript" id="transcript">Tap 'Accept' to connect with Alpha.</div>

    <div class="action-tray" id="tray">
        <button class="call-btn btn-decline" onclick="endCall()">Decline</button>
        <button class="call-btn btn-accept" onclick="answerCall()">Accept</button>
    </div>

    <audio id="audioPlayer" playsinline></audio>

    <script>
        let inCall = false;
        let isRecording = false;
        let mediaRecorder;
        let audioChunks = [];
        const statusEl = document.getElementById('status');
        const orb = document.getElementById('orb');
        const transcriptEl = document.getElementById('transcript');
        const tray = document.getElementById('tray');
        const audioPlayer = document.getElementById('audioPlayer');

        async function answerCall() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => {{ if (e.data.size > 0) audioChunks.push(e.data); }};
                mediaRecorder.onstop = sendAudioToServer;

                inCall = true;
                statusEl.innerText = "Connected";
                orb.className = "visualizer speaking";
                
                // Switch buttons to WhatsApp/FaceTime style speaker controls
                tray.innerHTML = `<button class="call-btn btn-speak" id="talkBtn" onclick="toggleRecord()">🎙️ Tap to Speak</button>`;

                const res = await fetch('/greet');
                const data = await res.json();
                transcriptEl.innerText = "Alpha: " + data.reply;
                playResponse(data.audio_url);
            }} catch (err) {{
                alert("Microphone permission zaroori hai: " + err);
            }}
        }}

        async function toggleRecord() {{
            const talkBtn = document.getElementById('talkBtn');
            if (!isRecording) {{
                audioPlayer.pause();
                audioChunks = [];
                mediaRecorder.start();
                isRecording = true;
                orb.className = "visualizer";
                statusEl.innerText = "Listening...";
                talkBtn.innerText = "🔴 Send Now";
                talkBtn.style.background = "#ff3b30";
            }} else {{
                mediaRecorder.stop();
                isRecording = false;
                orb.className = "visualizer speaking";
                statusEl.innerText = "Thinking...";
                talkBtn.innerText = "🎙️ Tap to Speak";
                talkBtn.style.background = "#007aff";
            }}
        }}

        async function sendAudioToServer() {{
            const blob = new Blob(audioChunks, {{ type: 'audio/webm' }});
            const formData = new FormData();
            formData.append("audio", blob, "speech.webm");

            try {{
                const res = await fetch('/talk', {{ method: 'POST', body: formData }});
                const data = await res.json();
                transcriptEl.innerText = "You: " + data.user_text + "\\nAlpha: " + data.reply;
                playResponse(data.audio_url);
            }} catch (e) {{
                statusEl.innerText = "Connection error!";
            }}
        }}

        function playResponse(url) {{
            statusEl.innerText = "Alpha Speaking...";
            audioPlayer.src = url + "?t=" + new Date().getTime();
            audioPlayer.play();
            audioPlayer.onended = () => {{
                statusEl.innerText = "Connected";
            }};
        }}

        function endCall() {{
            audioPlayer.pause();
            inCall = false;
            isRecording = false;
            statusEl.innerText = "Call Ended";
            orb.style.opacity = "0.3";
            tray.innerHTML = `<button class="call-btn btn-speak" style="background:#34c759;" onclick="location.reload()">Call Again</button>`;
        }}
    </script>
</body>
</html>
"""

async def generate_voice(text: str, output_file: str = "call_reply.mp3"):
    communicate = edge_tts.Communicate(text, VOICE_NAME, rate="+8%")
    await communicate.save(output_file)
    return output_file

@app.get("/greet")
async def greet_caller():
    greeting = f"Line connected Boss. Main online hoon, boliye kya hukam hai?"
    await generate_voice(greeting, "call_reply.mp3")
    return {"reply": greeting, "audio_url": "/audio"}

@app.post("/talk")
async def process_voice(audio: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(await audio.read())
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=("speech.webm", f.read()),
                model="whisper-large-v3-turbo",
                prompt="Lokesh talking to his AI assistant Alpha in Hinglish or English."
            )
        os.remove(tmp_path)
        user_text = transcription.text.strip()

        if not user_text:
            return {"user_text": "...", "reply": "Aawaz saaf nahi aayi Boss, dobara boliye?", "audio_url": "/audio"}

        conversation_memory.append({"role": "user", "content": user_text})
        chat_completion = client.chat.completions.create(
            messages=conversation_memory,
            model="llama-3.3-70b-versatile",
            temperature=0.6,
            max_tokens=120
        )
        reply = chat_completion.choices[0].message.content.strip()
        conversation_memory.append({"role": "assistant", "content": reply})

        await generate_voice(reply, "call_reply.mp3")
        return {"user_text": user_text, "reply": reply, "audio_url": "/audio"}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/audio")
async def get_audio():
    return FileResponse("call_reply.mp3", media_type="audio/mpeg")

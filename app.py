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
            "You are running 24/7 on the cloud and talking to him on a live phone call. "
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
    <title>Alpha Comms 24/7</title>
    <style>
        body {{
            margin: 0; background: #07090e; color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; flex-direction: column; align-items: center; justify-content: space-between;
            height: 100vh; padding: 35px 20px; box-sizing: border-box; overflow: hidden;
        }}
        .header {{ text-align: center; margin-top: 15px; }}
        .caller-id {{ font-size: 34px; font-weight: 700; letter-spacing: 2px; color: #00f0ff; }}
        .phone-badge {{
            display: inline-block; margin-top: 8px; padding: 5px 14px;
            background: #00e67618; border: 1px solid #00e67655; border-radius: 20px;
            font-size: 13px; color: #00e676;
        }}
        .call-status {{ font-size: 16px; color: #8a99ad; margin-top: 12px; }}
        .orb-container {{ display: flex; align-items: center; justify-content: center; flex: 1; }}
        .orb {{
            width: 155px; height: 155px; border-radius: 50%;
            background: radial-gradient(circle, #00f0ff 0%, #0044ff 60%, transparent 100%);
            box-shadow: 0 0 40px #00f0ff55; transition: all 0.25s ease;
        }}
        .orb.ringing {{
            background: radial-gradient(circle, #00e676 0%, #00796b 60%, transparent 100%);
            box-shadow: 0 0 80px #00e676cc;
            animation: ringPulse 0.5s infinite alternate;
        }}
        .orb.listening {{
            background: radial-gradient(circle, #ff0055 0%, #990033 60%, transparent 100%);
            box-shadow: 0 0 60px #ff0055aa; transform: scale(1.18);
        }}
        .orb.speaking {{
            animation: pulse 0.8s infinite alternate;
            box-shadow: 0 0 70px #00f0ffaa;
        }}
        @keyframes pulse {{ from {{ transform: scale(1.0); }} to {{ transform: scale(1.22); }} }}
        @keyframes ringPulse {{ from {{ transform: scale(0.95); }} to {{ transform: scale(1.25); }} }}
        .transcript {{
            text-align: center; font-size: 15px; color: #cfd8dc;
            min-height: 48px; max-width: 92%; margin-bottom: 20px; line-height: 1.4;
            white-space: pre-line;
        }}
        .controls {{ display: flex; gap: 14px; align-items: center; margin-bottom: 25px; flex-wrap: wrap; justify-content: center; }}
        .btn {{
            border: none; border-radius: 50px; padding: 16px 28px;
            font-size: 16px; font-weight: 600; cursor: pointer; transition: 0.2s;
        }}
        .btn-talk {{ background: #00f0ff; color: #05070a; box-shadow: 0 0 25px #00f0ff66; }}
        .btn-ring {{ background: #00e676; color: #05070a; }}
        .btn-end {{ background: #ff1744; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="caller-id">ALPHA 24/7</div>
        <div class="phone-badge">Cloud Satellite Active • {DEFAULT_PHONE_NUMBER}</div>
        <div class="call-status" id="status">Tap 'Answer / Call' to connect</div>
    </div>

    <div class="orb-container">
        <div class="orb" id="orb"></div>
    </div>

    <div class="transcript" id="transcript">24/7 Cloud Core Online (Zero Laptop Needed)</div>

    <div class="controls">
        <button class="btn btn-talk" id="actionBtn" onclick="handleAction()">Answer / Call</button>
        <button class="btn btn-ring" onclick="triggerPhoneRing()">Ring My Phone</button>
        <button class="btn btn-end" onclick="endCall()">End</button>
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
        const actionBtn = document.getElementById('actionBtn');
        const audioPlayer = document.getElementById('audioPlayer');

        function playRingtoneBeep() {{
            try {{
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.frequency.setValueAtTime(660, ctx.currentTime + 0.2);
                gain.gain.setValueAtTime(0.25, ctx.currentTime);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.45);
            }} catch (e) {{}}
        }}

        setInterval(async () => {{
            if (inCall) return;
            try {{
                const res = await fetch('/check-ring');
                const data = await res.json();
                if (data.ringing) {{
                    orb.className = "orb ringing";
                    statusEl.innerText = "INCOMING CALL FROM ALPHA...";
                    transcriptEl.innerText = data.reason;
                    actionBtn.innerText = "Accept Call";
                    playRingtoneBeep();
                }}
            }} catch (e) {{}}
        }}, 2000);

        async function handleAction() {{
            if (!inCall) {{
                await startCall();
            }} else {{
                await toggleRecording();
            }}
        }}

        async function startCall() {{
            try {{
                await fetch('/clear-ring');
                const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => {{ if (e.data.size > 0) audioChunks.push(e.data); }};
                mediaRecorder.onstop = sendAudioToServer;

                inCall = true;
                actionBtn.innerText = "Tap to Speak";
                statusEl.innerText = "Connected — Alpha Speaking...";

                const res = await fetch('/greet');
                const data = await res.json();
                transcriptEl.innerText = "Alpha: " + data.reply;
                playResponse(data.audio_url);
            }} catch (err) {{
                alert("Allow Mic Permission: " + err);
            }}
        }}

        async function toggleRecording() {{
            if (!isRecording) {{
                audioPlayer.pause();
                audioChunks = [];
                mediaRecorder.start();
                isRecording = true;
                orb.className = "orb listening";
                statusEl.innerText = "Listening... (Tap 'Send Now' when done)";
                actionBtn.innerText = "Send Now";
            }} else {{
                mediaRecorder.stop();
                isRecording = false;
                orb.className = "orb";
                statusEl.innerText = "Alpha is thinking...";
                actionBtn.innerText = "Tap to Speak";
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
                statusEl.innerText = "Connection failed!";
            }}
        }}

        function playResponse(url) {{
            orb.className = "orb speaking";
            statusEl.innerText = "Alpha Speaking...";
            audioPlayer.src = url + "?t=" + new Date().getTime();
            audioPlayer.play();
            audioPlayer.onended = () => {{
                orb.className = "orb";
                statusEl.innerText = "Connected — Tap to Speak";
            }};
        }}

        async function triggerPhoneRing() {{
            statusEl.innerText = "Dialing {DEFAULT_PHONE_NUMBER}...";
            const res = await fetch('/ring-me');
            const data = await res.json();
            statusEl.innerText = data.status;
        }}

        function endCall() {{
            fetch('/clear-ring');
            audioPlayer.pause();
            inCall = false;
            isRecording = false;
            orb.className = "orb";
            statusEl.innerText = "Call Ended";
            actionBtn.innerText = "Answer / Call";
        }}
    </script>
</body>
</html>
"""

async def generate_voice(text: str, output_file: str = "call_reply.mp3"):
    communicate = edge_tts.Communicate(text, VOICE_NAME, rate="+8%")
    await communicate.save(output_file)
    return output_file

@app.get("/check-ring")
async def check_ring():
    return incoming_ring_state

@app.get("/clear-ring")
async def clear_ring():
    incoming_ring_state["ringing"] = False
    return {"status": "cleared"}

@app.get("/greet")
async def greet_caller():
    greeting = f"24/7 Cloud Line connected Boss. Laptop band bhi ho toh main hamesha online hoon. Boliye kya hukam hai?"
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

        if "call me" in user_text.lower() or "call karna" in user_text.lower():
            threading.Thread(target=delayed_call, args=(15, "Boss, aapne bola tha wapas call karne ke liye!"), daemon=True).start()

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

@app.get("/ring-me")
async def alpha_calls_user(reason: str = "Boss, Alpha calling from 24/7 Cloud! Tap to pick up."):
    incoming_ring_state["ringing"] = True
    incoming_ring_state["reason"] = reason
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=reason.encode("utf-8"),
            headers={
                "Title": f"Incoming Call: ALPHA AI ({DEFAULT_PHONE_NUMBER})",
                "Priority": "urgent",
                "Tags": "telephone_receiver,rotating_light"
            },
            timeout=5
        )
    except Exception:
        pass
    return {"status": f"Ringing {DEFAULT_PHONE_NUMBER} from Cloud!"}

def delayed_call(seconds: int, reason: str):
    time.sleep(seconds)
    incoming_ring_state["ringing"] = True
    incoming_ring_state["reason"] = reason
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=reason.encode("utf-8"),
            headers={"Title": f"ALPHA AI Calling {DEFAULT_PHONE_NUMBER}", "Priority": "urgent"},
            timeout=5
        )
    except Exception:
        pass

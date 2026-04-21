from flask import Flask, request, jsonify, render_template_string, redirect, session
from query_engine import ask
from dotenv import load_dotenv
import requests
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

OW_URL = os.getenv("OPEN_WEARABLES_URL", "https://backend-production-c714.up.railway.app")
OW_API_KEY = os.getenv("OPEN_WEARABLES_API_KEY")

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Vitals AI</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, sans-serif; background: #0f0f0f; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }
    #header { padding: 16px 24px; border-bottom: 1px solid #222; display: flex; align-items: center; gap: 12px; }
    #header h1 { font-size: 18px; font-weight: 600; }
    #header span { font-size: 12px; color: #666; }
    #vitals { padding: 12px 24px; background: #161616; border-bottom: 1px solid #222; display: flex; gap: 24px; font-size: 13px; align-items: center; }
    .vital { display: flex; flex-direction: column; gap: 2px; }
    .vital-label { color: #666; font-size: 11px; }
    .vital-value { color: #e0e0e0; font-weight: 500; }
    .vital-value.low { color: #ef4444; }
    .vital-value.ok { color: #22c55e; }
    .connect-btn { margin-left: auto; background: #1d4ed8; border: none; border-radius: 8px; padding: 8px 16px; color: white; font-size: 13px; cursor: pointer; text-decoration: none; }
    .connect-btn:hover { background: #2563eb; }
    .connect-section { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; }
    .connect-card { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 32px; max-width: 400px; text-align: center; }
    .connect-card h2 { font-size: 18px; margin-bottom: 8px; }
    .connect-card p { color: #888; font-size: 14px; margin-bottom: 24px; line-height: 1.6; }
    .device-btns { display: flex; flex-direction: column; gap: 10px; }
    .device-btn { padding: 12px 20px; border-radius: 8px; border: 1px solid #333; background: #222; color: #e0e0e0; font-size: 14px; cursor: pointer; text-align: left; display: flex; align-items: center; gap: 10px; }
    .device-btn:hover { border-color: #555; background: #2a2a2a; }
    #messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
    .message { max-width: 800px; line-height: 1.6; }
    .message.user { align-self: flex-end; background: #1d4ed8; padding: 12px 16px; border-radius: 12px; font-size: 14px; }
    .message.assistant { align-self: flex-start; background: #1a1a1a; border: 1px solid #222; padding: 16px; border-radius: 12px; font-size: 14px; white-space: pre-wrap; }
    #starters { padding: 0 24px 16px; display: flex; gap: 8px; flex-wrap: wrap; }
    .starter { background: #1a1a1a; border: 1px solid #333; padding: 8px 14px; border-radius: 20px; font-size: 13px; cursor: pointer; color: #aaa; }
    .starter:hover { border-color: #555; color: #e0e0e0; }
    #input-area { padding: 16px 24px; border-top: 1px solid #222; display: flex; gap: 12px; }
    #input { flex: 1; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 12px 16px; color: #e0e0e0; font-size: 14px; outline: none; resize: none; height: 48px; }
    #input:focus { border-color: #555; }
    #send { background: #1d4ed8; border: none; border-radius: 8px; padding: 12px 20px; color: white; font-size: 14px; cursor: pointer; }
    #send:hover { background: #2563eb; }
    #send:disabled { background: #333; cursor: not-allowed; }
    .loading { color: #666; font-style: italic; }
  </style>
</head>
<body>
  <div id="header">
    <h1>Vitals AI</h1>
    <span>Research-backed performance intelligence</span>
  </div>

  {% if not connected %}
  <div id="vitals">
    <span style="color:#666;font-size:13px">No wearable connected</span>
    <a href="/connect" class="connect-btn">+ Connect Wearable</a>
  </div>
  <div class="connect-section">
    <div class="connect-card">
      <h2>Connect your wearable</h2>
      <p>Connect your device to get personalized answers based on your actual biometric data, grounded in peer-reviewed research.</p>
      <div class="device-btns">
        <a href="/connect/oura" class="device-btn">⭕ Connect Oura Ring</a>
        <a href="/connect/whoop" class="device-btn">💪 Connect WHOOP</a>
        <a href="/connect/garmin" class="device-btn">⌚ Connect Garmin</a>
      </div>
    </div>
  </div>
  {% else %}
  <div id="vitals">
    <div class="vital"><span class="vital-label">HRV</span><span class="vital-value {{ 'low' if vitals.hrv and vitals.hrv < 50 else 'ok' }}">{{ vitals.hrv or 'N/A' }}ms</span></div>
    <div class="vital"><span class="vital-label">Recovery</span><span class="vital-value {{ 'low' if vitals.recovery and vitals.recovery < 60 else 'ok' }}">{{ vitals.recovery or 'N/A' }}/100</span></div>
    <div class="vital"><span class="vital-label">Resting HR</span><span class="vital-value">{{ vitals.rhr or 'N/A' }} bpm</span></div>
    <div class="vital"><span class="vital-label">Sleep</span><span class="vital-value {{ 'ok' if vitals.sleep and vitals.sleep > 70 else 'low' }}">{{ vitals.sleep or 'N/A' }}/100</span></div>
    <div class="vital"><span class="vital-label">Device</span><span class="vital-value">{{ vitals.device or 'Wearable' }}</span></div>
    <a href="/disconnect" class="connect-btn" style="background:#333">Disconnect</a>
  </div>
  <div id="messages">
    <div class="message assistant">Your wearable is connected. Ask me anything about your biometric data and I'll answer using peer-reviewed research and your actual numbers.</div>
  </div>
  <div id="starters">
    <div class="starter" onclick="send('Should I train hard today?')">Should I train hard today?</div>
    <div class="starter" onclick="send('Why is my HRV low?')">Why is my HRV low?</div>
    <div class="starter" onclick="send('What does my recovery score mean?')">What does my recovery score mean?</div>
    <div class="starter" onclick="send('How can I improve my HRV?')">How can I improve my HRV?</div>
  </div>
  <div id="input-area">
    <textarea id="input" placeholder="Ask about your vitals..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMsg()}"></textarea>
    <button id="send" onclick="sendMsg()">Send</button>
  </div>
  <script>
    const VITALS = `{{ vitals_str }}`;
    let history = [];
    function send(text) { document.getElementById('input').value = text; sendMsg(); }
    async function sendMsg() {
      const input = document.getElementById('input');
      const question = input.value.trim();
      if (!question) return;
      input.value = '';
      document.getElementById('send').disabled = true;
      document.getElementById('starters').style.display = 'none';
      const messages = document.getElementById('messages');
      const userDiv = document.createElement('div');
      userDiv.className = 'message user';
      userDiv.textContent = question;
      messages.appendChild(userDiv);
      const loadingDiv = document.createElement('div');
      loadingDiv.className = 'message assistant loading';
      loadingDiv.textContent = 'Searching research papers...';
      messages.appendChild(loadingDiv);
      messages.scrollTop = messages.scrollHeight;
      try {
        const res = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({question, vitals: VITALS, history})
        });
        const data = await res.json();
        loadingDiv.className = 'message assistant';
        loadingDiv.textContent = data.answer;
        history.push({role: 'user', content: question});
        history.push({role: 'assistant', content: data.answer});
      } catch(e) {
        loadingDiv.textContent = 'Error — check terminal for details.';
      }
      document.getElementById('send').disabled = false;
      messages.scrollTop = messages.scrollHeight;
    }
  </script>
  {% endif %}
</body>
</html>
"""

def get_ow_headers():
    return {"X-Open-Wearables-API-Key": OW_API_KEY}

def create_ow_user(email):
    res = requests.post(f"{OW_URL}/api/v1/users",
        headers=get_ow_headers(),
        json={"email": email}
    )
    return res.json()

def get_connect_url(user_id, provider):
    res = requests.get(
        f"{OW_URL}/api/v1/oauth/{provider}/authorize",
        headers=get_ow_headers(),
        params={"user_id": user_id}
    )
    data = res.json()
    return data.get("url") or data.get("authorization_url")

def get_user_vitals(user_id):
    res = requests.get(f"{OW_URL}/api/v1/users/{user_id}/data/latest",
        headers=get_ow_headers()
    )
    data = res.json()
    return {
        "hrv": data.get("hrv"),
        "recovery": data.get("recovery_score"),
        "rhr": data.get("resting_heart_rate"),
        "sleep": data.get("sleep_score"),
        "device": data.get("provider", "Wearable")
    }

@app.route('/')
def index():
    connected = 'user_id' in session
    vitals = {}
    vitals_str = ""
    if connected:
        try:
            vitals = get_user_vitals(session['user_id'])
            vitals_str = f"""
- HRV: {vitals.get('hrv')}ms
- Recovery score: {vitals.get('recovery')}/100
- Resting heart rate: {vitals.get('rhr')} bpm
- Sleep score: {vitals.get('sleep')}/100
- Device: {vitals.get('device')}"""
        except:
            vitals_str = "Wearable connected but no data yet."
    return render_template_string(HTML, connected=connected, vitals=vitals, vitals_str=vitals_str)

@app.route('/connect/oura')
def connect_oura():
    user = create_ow_user(f"user_{os.urandom(4).hex()}@vitalsai.app")
    user_id = user.get("id")
    if user_id:
        session['user_id'] = user_id
        url = get_connect_url(user_id, "oura")
        if url:
            return redirect(url)
    return "Error connecting to Oura", 500

@app.route('/connect/whoop')
def connect_whoop():
    user = create_ow_user(f"user_{os.urandom(4).hex()}@vitalsai.app")
    user_id = user.get("id")
    if user_id:
        session['user_id'] = user_id
        url = get_connect_url(user_id, "whoop")
        if url:
            return redirect(url)
    return "Error connecting to WHOOP", 500

@app.route('/connect/garmin')
def connect_garmin():
    user = create_ow_user(f"user_{os.urandom(4).hex()}@vitalsai.app")
    user_id = user.get("id")
    if user_id:
        session['user_id'] = user_id
        url = get_connect_url(user_id, "garmin")
        if url:
            return redirect(url)
    return "Error connecting to Garmin", 500

@app.route('/disconnect')
def disconnect():
    session.clear()
    return redirect('/')

@app.route('/ask', methods=['POST'])
def ask_endpoint():
    data = request.json
    question = data.get('question', '')
    vitals = data.get('vitals', '')
    history = data.get('history', [])
    answer = ask(question, user_vitals=vitals, history=history)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)

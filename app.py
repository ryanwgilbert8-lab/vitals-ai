from flask import Flask, request, jsonify, render_template_string
from query_engine import ask
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

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
    #vitals { padding: 12px 24px; background: #161616; border-bottom: 1px solid #222; display: flex; gap: 24px; font-size: 13px; }
    .vital { display: flex; flex-direction: column; gap: 2px; }
    .vital-label { color: #666; font-size: 11px; }
    .vital-value { color: #e0e0e0; font-weight: 500; }
    .vital-value.low { color: #ef4444; }
    .vital-value.ok { color: #22c55e; }
    #messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
    .message { max-width: 800px; line-height: 1.6; }
    .message.user { align-self: flex-end; background: #1d4ed8; padding: 12px 16px; border-radius: 12px; font-size: 14px; }
    .message.assistant { align-self: flex-start; background: #1a1a1a; border: 1px solid #222; padding: 16px; border-radius: 12px; font-size: 14px; white-space: pre-wrap; }
    .message.assistant h1, .message.assistant h2, .message.assistant h3 { margin: 12px 0 6px; font-size: 15px; }
    .message.assistant table { border-collapse: collapse; margin: 8px 0; font-size: 13px; }
    .message.assistant td, .message.assistant th { border: 1px solid #333; padding: 6px 10px; }
    .message.assistant th { background: #222; }
    #starters { padding: 0 24px 16px; display: flex; gap: 8px; flex-wrap: wrap; }
    .starter { background: #1a1a1a; border: 1px solid #333; padding: 8px 14px; border-radius: 20px; font-size: 13px; cursor: pointer; color: #aaa; }
    .starter:hover { border-color: #555; color: #e0e0e0; }
    #input-area { padding: 16px 24px; border-top: 1px solid #222; display: flex; gap: 12px; }
    #input { flex: 1; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 12px 16px; color: #e0e0e0; font-size: 14px; outline: none; resize: none; height: 48px; }
    #input:focus { border-color: #555; }
    #send { background: #1d4ed8; border: none; border-radius: 8px; padding: 12px 20px; color: white; font-size: 14px; cursor: pointer; white-space: nowrap; }
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
  <div id="vitals">
    <div class="vital"><span class="vital-label">HRV</span><span class="vital-value low">38ms</span></div>
    <div class="vital"><span class="vital-label">Recovery</span><span class="vital-value low">41/100</span></div>
    <div class="vital"><span class="vital-label">Resting HR</span><span class="vital-value low">62 bpm</span></div>
    <div class="vital"><span class="vital-label">Sleep</span><span class="vital-value ok">71/100</span></div>
    <div class="vital"><span class="vital-label">Device</span><span class="vital-value">Oura Ring</span></div>
  </div>
  <div id="messages">
    <div class="message assistant">Ask me anything about your biometric data. I'll answer using peer-reviewed research and your actual numbers.\n\nTry: "Should I train hard today?" or "Why is my HRV low?"</div>
  </div>
  <div id="starters">
    <div class="starter" onclick="send('Should I train hard today?')">Should I train hard today?</div>
    <div class="starter" onclick="send('Why is my HRV so low?')">Why is my HRV so low?</div>
    <div class="starter" onclick="send('What does my recovery score mean?')">What does my recovery score mean?</div>
    <div class="starter" onclick="send('How can I improve my HRV?')">How can I improve my HRV?</div>
  </div>
  <div id="input-area">
    <textarea id="input" placeholder="Ask about your vitals..." onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMsg()}"></textarea>
    <button id="send" onclick="sendMsg()">Send</button>
  </div>
  <script>
    const VITALS = `- HRV: 38ms (personal avg: 58ms, down 35% over 10 days)
- Recovery score: 41/100
- Resting heart rate: 62 bpm (personal avg: 54 bpm)
- Sleep score: 71/100
- Sleep duration: 7.2 hours
- Device: Oura Ring`;

    let history = [];

    function send(text) {
      document.getElementById('input').value = text;
      sendMsg();
    }

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
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/ask', methods=['POST'])
def ask_endpoint():
    data = request.json
    question = data.get('question', '')
    vitals = data.get('vitals', '')
    history = data.get('history', [])
    answer = ask(question, user_vitals=vitals, history=history)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    app.run(debug=True, port=5001)

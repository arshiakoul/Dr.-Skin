# ngrok_flask_html.py
# NOTE: Replace NGROK_AUTH_TOKEN and NGROK_PATH with your own values.

from flask import Flask, request, render_template_string, jsonify
from skin_cancer_backend import predict, generate_gpt_response
import os, base64
from pyngrok import ngrok, conf

# --------------------------
# 1) ngrok config
# --------------------------
NGROK_AUTH_TOKEN = "31KGslGm0xgtj0GQ6NoydsmVhVL_5mAzytc2kJxJhLzB3aSfD"  # ← replace with your token
NGROK_PATH = r"C:\Users\aisha\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe"  # ← path to ngrok.exe

conf.get_default().ngrok_path = NGROK_PATH
conf.get_default().auth_token = NGROK_AUTH_TOKEN

# --------------------------
# 2) Flask app setup
# --------------------------
app = Flask(__name__)
last_result = "No current detection"

# Load Dr. Skin logo as base64 (expects logo.svg next to this file)
if os.path.exists("logo.svg"):
    with open("logo.svg", "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")
else:
    logo_base64 = ""

# --------------------------
# 3) HTML (Inter + modern card/hero layout, Instagram-like chat)
#    - Keeps your palette:
#      #081F5C (navy), #7096D1 (primary), #EDF1F6 (bg), #D0E3FF (bot), #F7F2EB (chat area bg)
#    - Replaces peach accents with a cool blue #AFCBFF
#    - Bigger Dr. Skin avatar outside chat bubble
#    - Typing/thinking animation
#    - Auto "diagnosis" message on Analyze
#    - Camera capture (file input + optional live camera modal)
# --------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Doctor Skin</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root{
    --navy:#081F5C;
    --primary:#7096D1;
    --bg:#EDF1F6;
    --bot:#D0E3FF;
    --chatbg:#F7F2EB;
    --accent:#AFCBFF; /* cool blue replaces peach */
    --text:#0b1a3a;
    --card:#ffffff;
    --ring: rgba(8,31,92,0.08);
  }
  *{ box-sizing:border-box; }
  body{
    margin:0;
    background: var(--bg);
    color: var(--text);
    font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  }

  /* Hero (like the screenshot vibe) */
  .hero{
    position:relative;
    background: radial-gradient(1200px 600px at -10% -20%, #2b4ca8 0%, var(--navy) 50%, #0a1647 100%);
    color:#fff;
    padding: 32px 20px 80px;
    overflow:hidden;
  }
  .hero .container{
    width: min(1100px, 92%);
    margin: 0 auto;
    display:grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 24px;
    align-items:center;
  }
  .brand{
    display:flex; align-items:center; gap:12px; margin-bottom:18px;
  }
  .brand img{ height:56px; width:56px; background:#fff; border-radius:12px; padding:6px; }
  .brand h1{ margin:0; font-weight:800; font-size: clamp(24px, 4vw, 34px); letter-spacing: -0.02em; }
  .hero h2{
    margin: 8px 0 10px;
    font-size: clamp(26px, 5vw, 44px);
    line-height:1.1;
    font-weight:800;
  }
  .hero p{
    margin: 0 0 18px;
    font-size: clamp(14px, 2.2vw, 16px);
    opacity: 0.9;
  }
  .hero .pill{
    display:inline-flex; align-items:center; gap:8px;
    background: rgba(255,255,255,0.12);
    padding:8px 12px; border-radius:999px; font-weight:600;
    border: 1px solid rgba(255,255,255,0.18);
    margin-bottom:10px;
  }
  .hero-card{
    background:#fff; color:var(--text);
    border-radius:20px;
    padding:16px;
    box-shadow: 0 10px 35px var(--ring);
    border:1px solid #eaf0ff;
  }
  .hero-media{
    background: linear-gradient(135deg, var(--accent), #cfe0ff);
    border:1px solid #eaf0ff; border-radius: 20px;
    box-shadow: 0 10px 35px var(--ring);
    padding: 12px;
  }

  /* Main content grid */
  .main{
    width: min(1100px, 92%);
    margin: 50px auto 40px; /* lift cards into hero area */
    display:grid; grid-template-columns: 1.1fr 0.9fr; gap: 20px;
  }

  .card{
    background: var(--card);
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 10px 30px var(--ring);
    border:1px solid #e9eefb;
  }
  .card h3{
    margin:4px 0 14px; font-size: 18px; font-weight: 700; color: var(--navy);
  }

  /* Uploader */
  .upload-wrap{
    display:flex; flex-direction:column; gap:10px;
  }
  .controls{
    display:flex; flex-wrap:wrap; gap:8px;
  }
  input[type="file"]{
    padding:10px; border:1px dashed #c9d8ff; border-radius:12px; background:#f7f9ff; width:100%;
  }
  button{
    padding: 10px 14px;
    border-radius: 12px;
    border: none;
    background: var(--primary);
    color:#fff; font-weight:600; cursor:pointer;
  }
  button.secondary{ background:#e8efff; color: var(--navy); }
  button.ghost{ background:transparent; color: var(--navy); border:1px solid #cfd9ff; }
  button:disabled{ opacity:0.7; cursor:not-allowed; }

  .image-preview{
    position:relative; display:none; margin-top:6px;
  }
  .image-preview img{
    width:100%; border-radius: 14px; border: 2px solid #D0E3FF;
  }
  .image-preview .hide-btn{
    position:absolute; top:10px; right:10px;
    background:#ffffffdd; color:var(--navy); border:1px solid #d8e4ff; border-radius:10px; padding:6px 10px; font-weight:600;
  }

  .result{
    margin-top:10px; font-weight:700; color:var(--navy);
  }

  /* Chat */
  .chat{
    display:flex; flex-direction:column; gap:10px;
  }
  .chatbox{
    background: var(--chatbg);
    border-radius: 16px; padding: 12px; height: 380px; overflow:auto;
    border:1px solid #efe8dc;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
  }

  /* Message rows with avatar outside bubble */
  .row{
    display:flex; align-items:flex-end; gap:10px; margin: 10px 0;
  }
  .row.user{ justify-content:flex-end; }
  .row .avatar{
    flex: 0 0 auto;
    width: 42px; height:42px; border-radius: 12px;
    display:flex; align-items:center; justify-content:center;
    background:#fff; border:1px solid #e3eaff; box-shadow:0 2px 10px var(--ring);
  }
  .row .avatar img{ width: 80%; height: 80%; object-fit: contain; }
  .bubble{
    max-width: min(76%, 560px);
    padding: 10px 14px; border-radius: 16px; font-size: 14px; line-height:1.45;
    box-shadow: 0 2px 10px var(--ring); border:1px solid rgba(0,0,0,0.04);
  }
  .row.bot .bubble{
    background: var(--bot);
    color: var(--navy);
    border-bottom-left-radius: 6px;
  }
  .row.user .bubble{
    background: var(--primary); color:#fff;
    border-bottom-right-radius: 6px;
  }

  .chat-input{
    display:flex; gap:8px;
  }
  .chat-input input{
    flex:1; padding: 12px 14px; border-radius: 12px; border:1px solid #cfd9ff; background:#fff;
    font-family:inherit;
  }

  /* Typing/thinking animation */
  .thinking{ display:inline-flex; gap:5px; align-items:center; }
  .thinking span{
    width:8px; height:8px; background: var(--navy); border-radius:50%;
    animation: bounce 1.2s infinite ease-in-out;
  }
  .thinking span:nth-child(2){ animation-delay: .15s; }
  .thinking span:nth-child(3){ animation-delay: .3s; }
  @keyframes bounce{
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
  }

  /* Camera modal */
  .modal{
    position:fixed; inset:0; background: rgba(0,0,0,0.45);
    display:none; align-items:center; justify-content:center; z-index: 50;
  }
  .modal .sheet{
    width:min(720px, 92%); background:#fff; border-radius:18px; padding:12px;
    box-shadow: 0 30px 80px rgba(0,0,0,0.3);
  }
  .cam-wrap{ position:relative; background:#000; border-radius:14px; overflow:hidden; }
  video, canvas{ width:100%; height:auto; display:block; }
  .modal .actions{ display:flex; gap:8px; margin-top:10px; justify-content:flex-end; }

  @media (max-width: 880px){
    .hero .container, .main{ grid-template-columns: 1fr; }
    .main{ margin-top: -40px; }
  }
</style>
</head>
<body>

<!-- HERO -->
<section class="hero">
  <div class="container">
    <div>
      <div class="brand">
        {% if logo_base64 %}<img src="data:image/svg+xml;base64,{{logo_base64}}" alt="Dr. Skin">{% endif %}
        <h1>Dr. Skin</h1>
      </div>
      <div class="pill">Skin lesion screening • Private • Instant</div>
      <h2>Fast, private, AI-assisted skin checks.</h2>
      <p>Upload or take a photo. Dr. Skin will analyze and explain the likely diagnosis in plain language.</p>
    </div>
    <div class="hero-media">
      <div class="hero-card">
        <strong style="color:var(--navy);">Safe & On-device preview</strong><br>
        Snap a clear, well-lit close-up of the lesion for best results.
      </div>
    </div>
  </div>
</section>

<!-- MAIN -->
<main class="main">
  <!-- LEFT: Upload/Analyze -->
  <section class="card">
    <h3>Upload or Take a Skin Image</h3>
    <form id="uploadForm" class="upload-wrap" enctype="multipart/form-data">
      <input type="file" name="file" id="fileInput" accept="image/*" capture="environment">
      <div class="controls">
        <button type="submit" id="analyzeBtn">Analyze</button>
        <button type="button" id="toggleImageBtn" class="secondary">Show/Hide Image</button>
        <button type="button" id="openCameraBtn" class="ghost">Use Camera</button>
      </div>
    </form>

    <div class="image-preview" id="imagePreviewWrap">
      <img id="imagePreview" alt="Preview">
      <button class="hide-btn" id="hidePreview">Hide</button>
    </div>

    <p class="result" id="result"></p>
  </section>

  <!-- RIGHT: Chat -->
  <section class="card">
    <h3>Ask Dr. Skin About Your Result</h3>
    <div class="chat">
      <div class="chatbox" id="chatBox"></div>
      <div class="chat-input">
        <input type="text" id="chatInput" placeholder="Ask a question…" />
        <button id="chatSend">Send</button>
      </div>
    </div>
  </section>
</main>

<!-- Camera Modal -->
<div class="modal" id="cameraModal">
  <div class="sheet">
    <h3 style="margin:6px 6px 10px; color:var(--navy);">Take a Photo</h3>
    <div class="cam-wrap">
      <video id="video" autoplay playsinline></video>
      <canvas id="canvas" style="display:none;"></canvas>
    </div>
    <div class="actions">
      <button id="snapBtn" class="secondary">Capture</button>
      <button id="usePhotoBtn" disabled>Use Photo</button>
      <button id="closeCameraBtn" class="ghost">Close</button>
    </div>
  </div>
</div>

<script>
  // Elements
  const fileInput = document.getElementById("fileInput");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const resultEl = document.getElementById("result");
  const img = document.getElementById("imagePreview");
  const previewWrap = document.getElementById("imagePreviewWrap");
  const toggleImageBtn = document.getElementById("toggleImageBtn");
  const hidePreviewBtn = document.getElementById("hidePreview");
  const chatBox = document.getElementById("chatBox");
  const chatInput = document.getElementById("chatInput");
  const chatSend = document.getElementById("chatSend");

  // Camera modal elements
  const cameraModal = document.getElementById("cameraModal");
  const openCameraBtn = document.getElementById("openCameraBtn");
  const closeCameraBtn = document.getElementById("closeCameraBtn");
  const snapBtn = document.getElementById("snapBtn");
  const usePhotoBtn = document.getElementById("usePhotoBtn");
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  let stream = null;
  let snappedBlob = null;

  // Helper: append user message row
  function appendUser(msg){
    const row = document.createElement("div");
    row.className = "row user";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = msg;
    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Helper: typing indicator with Dr. Skin avatar
  function appendThinking(){
    const row = document.createElement("div");
    row.className = "row bot";
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = '<img src="data:image/svg+xml;base64,{{logo_base64}}" alt="Dr. Skin">';
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = '<div class="thinking"><span></span><span></span><span></span></div>';
    row.appendChild(avatar);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
    return row;
  }

  // Helper: append Dr. Skin message with avatar (logo outside bubble)
  function appendBot(msg){
    const row = document.createElement("div");
    row.className = "row bot";
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.innerHTML = '<img src="data:image/svg+xml;base64,{{logo_base64}}" alt="Dr. Skin">';
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = '<strong>Dr. Skin:</strong> ' + msg;
    row.appendChild(avatar);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // Load preview on file select
  fileInput.addEventListener("change", function(){
    const file = this.files[0];
    if (!file) return;
    const rd = new FileReader();
    rd.onload = (e)=>{
      img.src = e.target.result;
      previewWrap.style.display = "block";
    };
    rd.readAsDataURL(file);
  });

  // Toggle preview
  toggleImageBtn.addEventListener("click", ()=>{
    if (previewWrap.style.display === "none" || !previewWrap.style.display){
      if (img.src) previewWrap.style.display = "block";
    } else {
      previewWrap.style.display = "none";
    }
  });
  hidePreviewBtn.addEventListener("click", ()=> previewWrap.style.display = "none");

  // Submit for analysis
  document.getElementById("uploadForm").addEventListener("submit", function(e){
    e.preventDefault();
    const formData = new FormData();

    // Prefer snapped photo if available, else file input
    if (snappedBlob){
      formData.append("file", snappedBlob, "camera.jpg");
    } else if (fileInput.files[0]){
      formData.append("file", fileInput.files[0]);
    } else {
      resultEl.textContent = "Please choose or take a photo first.";
      return;
    }

    // Disable Analyze & show subtle loading state
    analyzeBtn.disabled = true;
    const oldText = analyzeBtn.textContent;
    analyzeBtn.textContent = "Analyzing…";

    // Also show a typing indicator in chat
    const thinkingNode = appendThinking();

    fetch("/upload", { method: "POST", body: formData })
      .then(r => r.json())
      .then(data => {
        resultEl.textContent = data.message || "Done.";
        // Remove thinking, add bot diagnosis message
        thinkingNode.remove();
        appendBot(data.message || "Here’s my analysis.");
      })
      .catch(err => {
        thinkingNode.remove();
        resultEl.textContent = "Error analyzing image.";
        appendBot("Hmm, I couldn’t analyze that image. Please try again with a clear, well-lit close-up.");
      })
      .finally(()=>{
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = oldText;
        // Reset one-time snapped blob (optional)
        // snappedBlob = null;
      });
  });

  // Chat send
  function sendChat(){
    const msg = chatInput.value.trim();
    if (!msg) return;
    appendUser(msg);
    chatInput.value = "";

    const thinkingNode = appendThinking();
    fetch("/chat", {
      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ message: msg })
    })
    .then(r=>r.json())
    .then(data=>{
      thinkingNode.remove();
      appendBot(data.message || "I’m here to help with your result.");
    })
    .catch(()=>{
      thinkingNode.remove();
      appendBot("I had trouble responding. Please try again.");
    });
  }

  chatSend.addEventListener("click", sendChat);
  chatInput.addEventListener("keydown", (e)=>{ if(e.key==="Enter") sendChat(); });

  // -------- Live Camera Modal (optional) --------
  async function openCamera(){
    try{
      cameraModal.style.display = "flex";
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      video.srcObject = stream;
      snappedBlob = null;
      usePhotoBtn.disabled = true;
    } catch(err){
      cameraModal.style.display = "none";
      alert("Camera not available: " + err.message);
    }
  }

  function closeCamera(){
    cameraModal.style.display = "none";
    if (stream){
      stream.getTracks().forEach(t=>t.stop());
      stream = null;
    }
  }

  function snap(){
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    canvas.toBlob((blob)=>{
      if (blob){
        snappedBlob = blob;
        usePhotoBtn.disabled = false;
      }
    }, "image/jpeg", 0.95);
  }

  function usePhoto(){
    if (!snappedBlob) return;
    // Preview snapped image
    const reader = new FileReader();
    reader.onload = (e)=>{
      img.src = e.target.result;
      previewWrap.style.display = "block";
    };
    reader.readAsDataURL(snappedBlob);
    closeCamera();
  }

  openCameraBtn.addEventListener("click", openCamera);
  closeCameraBtn.addEventListener("click", closeCamera);
  snapBtn.addEventListener("click", snap);
  usePhotoBtn.addEventListener("click", usePhoto);

</script>
</body>
</html>
"""

# --------------------------
# 4) Routes
# --------------------------
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, logo_base64=logo_base64)

@app.route("/upload", methods=["POST"])
def upload_image():
    global last_result
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            file_path = f"temp_{file.filename}"
            file.save(file_path)
            try:
                last_result = predict(file_path)
                os.remove(file_path)
                return jsonify({"message": f"You may have: {last_result}"})
            except Exception as e:
                try:
                    os.remove(file_path)
                except Exception:
                    pass
                return jsonify({"message": f"Error analyzing image: {e}"})
    return jsonify({"message": "No file uploaded"})

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    try:
        response = generate_gpt_response(user_input, last_result)
        return jsonify({"message": response})
    except Exception as e:
        return jsonify({"message": f"Error generating response: {e}"})


# --------------------------
# 5) Run with ngrok
# --------------------------
if __name__ == "__main__":
    port = 4001
    public_url = ngrok.connect(port)
    print(f" * ngrok tunnel: {public_url}")
    app.run(port=port)

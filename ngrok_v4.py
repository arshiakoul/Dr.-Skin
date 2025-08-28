# ngrok_flask_html.py
from flask import Flask, request, render_template_string, jsonify
from skin_cancer_backend import predict, generate_gpt_response
import os, base64
from pyngrok import ngrok, conf

# --------------------------
# 1️⃣ Configure ngrok
# --------------------------
NGROK_AUTH_TOKEN = "31KGslGm0xgtj0GQ6NoydsmVhVL_5mAzytc2kJxJhLzB3aSfD"
NGROK_PATH = r"C:\Users\aisha\Downloads\ngrok-v3-stable-windows-amd64\ngrok.exe"

conf.get_default().ngrok_path = NGROK_PATH
conf.get_default().auth_token = NGROK_AUTH_TOKEN

# --------------------------
# 2️⃣ Flask app setup
# --------------------------
app = Flask(__name__)
last_result = "No current detection"

# Load logo for Dr. Skin
if os.path.exists("logo.svg"):
    with open("logo.svg", "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")
else:
    logo_base64 = ""

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Doctor Skin</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
    body {
        font-family: 'Inter', sans-serif;
        background: #EDF1F6;
        margin: 0;
        padding: 0;
    }
    header {
        background: #081F5C;
        color: white;
        padding: 10px;
        text-align: center;
    }
    header img {
        height: 50px;
        vertical-align: middle;
        border-radius: 8px;
        background: white;
        margin-left: 8px;
        padding: 3px;
    }
    header h2 {
        display: inline-block;
        margin: 0;
        font-size: 1.5rem;
        vertical-align: middle;
    }
    .container {
        width: 95%;
        max-width: 600px;
        margin: auto;
        padding: 10px;
    }
    .section {
        background: white;
        padding: 15px;
        margin-top: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    input, button {
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #ccc;
        font-size: 14px;
        font-family: 'Inter', sans-serif;
    }
    button {
        background: #7096D1;
        color: white;
        border: none;
        cursor: pointer;
    }
    button:hover {
        background: #081F5C;
    }
    #imagePreview {
        max-width: 100%;
        margin-top: 10px;
        border-radius: 8px;
        display: none;
        border: 2px solid #D0E3FF;
    }
    #result {
        margin-top: 8px;
        font-weight: bold;
        color: #081F5C;
    }
    .chat-box {
        background: #F7F2EB;
        padding: 10px;
        height: 300px;
        overflow-y: auto;
        border-radius: 10px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .message {
        max-width: 80%;
        padding: 8px 12px;
        border-radius: 16px;
        font-size: 14px;
        line-height: 1.4;
        display: flex;
        align-items: center;
    }
    .user {
        align-self: flex-end;
        background: #7096D1;
        color: white;
        border-bottom-right-radius: 4px;
    }
    .bot {
        align-self: flex-start;
        background: #D0E3FF;
        color: #081F5C;
        border-bottom-left-radius: 4px;
    }
    .bot img {
        height: 24px;
        width: 24px;
        margin-right: 8px;
        border-radius: 50%;
        background: white;
        padding: 2px;
    }
    .chat-input {
        display: flex;
        gap: 5px;
        margin-top: 8px;
    }
    .chat-input input {
        flex: 1;
    }
</style>
</head>
<body>
<header>
    <h2>Doctor Skin{% if logo_base64 %}<img src="data:image/svg+xml;base64,{{logo_base64}}">{% endif %}</h2>
</header>
<div class="container">

    <div class="section">
        <h3>Upload or Take a Skin Image</h3>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" name="file" id="fileInput" accept="image/*" capture="environment">
            <button type="submit">Analyze</button>
            <button type="button" id="toggleImageBtn">Show/Hide Image</button>
        </form>
        <img id="imagePreview">
        <p id="result"></p>
    </div>

    <div class="section">
        <h3>Ask Dr. Skin About Your Result</h3>
        <div class="chat-box" id="chatBox"></div>
        <div class="chat-input">
            <input type="text" id="chatInput" placeholder="Ask a question...">
            <button id="chatSend">Send</button>
        </div>
    </div>

</div>

<script>
document.getElementById("fileInput").addEventListener("change", function(){
    const file = this.files[0];
    if (file){
        const reader = new FileReader();
        reader.onload = function(e){
            const img = document.getElementById("imagePreview");
            img.src = e.target.result;
            img.style.display = "block";
        }
        reader.readAsDataURL(file);
    }
});

document.getElementById("toggleImageBtn").addEventListener("click", function(){
    const img = document.getElementById("imagePreview");
    img.style.display = (img.style.display === "none" || img.style.display === "") ? "block" : "none";
});

document.getElementById("uploadForm").addEventListener("submit", function(e){
    e.preventDefault();
    const formData = new FormData(this);
    fetch("/upload", { method: "POST", body: formData })
    .then(res => res.json())
    .then(data => {
        document.getElementById("result").innerText = data.message;
    });
});

document.getElementById("chatSend").addEventListener("click", function(){
    const input = document.getElementById("chatInput");
    const message = input.value.trim();
    if (!message) return;
    const chatBox = document.getElementById("chatBox");

    // User message
    const userDiv = document.createElement("div");
    userDiv.className = "message user";
    userDiv.textContent = message;
    chatBox.appendChild(userDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    input.value = "";

    // Fetch bot reply
    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
    }).then(res => res.json())
      .then(data => {
        const botDiv = document.createElement("div");
        botDiv.className = "message bot";

        // Add Dr. Skin avatar + name
        const img = document.createElement("img");
        img.src = "data:image/svg+xml;base64,{{logo_base64}}";
        botDiv.appendChild(img);

        const span = document.createElement("span");
        span.innerHTML = "<strong>Dr. Skin:</strong> " + data.message;
        botDiv.appendChild(span);

        chatBox.appendChild(botDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
      });
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, logo_base64=logo_base64)

@app.route("/upload", methods=["POST"])
def upload_image():
    global last_result
    if "file" in request.files:
        file = request.files["file"]
        if file.filename:
            file_path = f"temp_{file.filename}"
            file.save(file_path)
            try:
                last_result = predict(file_path)
                os.remove(file_path)
                return jsonify({"message": f"You may have: {last_result}"})
            except Exception as e:
                return jsonify({"message": f"Error analyzing image: {e}"})
    return jsonify({"message": "No file uploaded"})

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "")
    try:
        response = generate_gpt_response(user_input, last_result)
        return jsonify({"message": response})
    except Exception as e:
        return jsonify({"message": f"Error generating response: {e}"})

if __name__ == "__main__":
    port = 4001
    public_url = ngrok.connect(port)
    print(f" * ngrok tunnel: {public_url}")
    app.run(port=port)

from flask import Flask, request, render_template_string, jsonify
from flask_ngrok import run_with_ngrok
import os, base64

# --- IMPORT YOUR OWN MODEL & CHAT LOGIC ---
# These functions must exist in your own backend code.
# Replace `skin_cancer_backend` with your actual file if needed.
try:
    from skin_cancer_backend import predict, generate_gpt_response
except ImportError:
    def predict(path):
        return "Example Skin Condition"
    def generate_gpt_response(user_input, last_result):
        return f"Mock GPT: You asked '{user_input}', last detection was '{last_result}'."

# Flask setup
app = Flask(__name__)
run_with_ngrok(app)  # Auto public URL
last_result = "No current detection"

# --- EMBED LOGO AS BASE64 ---
if os.path.exists("logo.svg"):
    with open("logo.svg", "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")
else:
    logo_base64 = ""  # If no logo

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Skin Cancer Detection</title>
    <style>
        body { font-family: Arial; background: #f0f8ff; margin: 0; padding: 0; }
        header { background: #003366; color: white; padding: 15px; text-align: center; }
        .container { width: 80%; margin: auto; padding: 20px; }
        .upload-section, .chat-section {
            background: white; padding: 20px; margin-top: 20px; border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        input[type=file], button {
            padding: 10px; margin-top: 10px;
        }
        #imagePreview { max-width: 300px; display: block; margin-top: 10px; }
        .chat-box { border: 1px solid #ccc; padding: 10px; height: 200px; overflow-y: auto; }
        .chat-input { display: flex; margin-top: 10px; }
        .chat-input input { flex: 1; padding: 10px; }
        .chat-input button { padding: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>Skin Cancer Detection</h1>
        {% if logo_base64 %}
        <img src="data:image/svg+xml;base64,{{logo_base64}}" height="50">
        {% endif %}
    </header>
    <div class="container">

        <!-- Upload Section -->
        <div class="upload-section">
            <h2>Upload Skin Image</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" name="file" id="fileInput" accept="image/*">
                <button type="submit">Analyze</button>
            </form>
            <img id="imagePreview" style="display:none;">
            <p id="result"></p>
        </div>

        <!-- Chat Section -->
        <div class="chat-section">
            <h2>Ask About Your Result</h2>
            <div class="chat-box" id="chatBox"></div>
            <div class="chat-input">
                <input type="text" id="chatInput" placeholder="Ask a question...">
                <button id="chatSend">Send</button>
            </div>
        </div>

    </div>

    <script>
        // Preview uploaded image
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

        // Handle image upload
        document.getElementById("uploadForm").addEventListener("submit", function(e){
            e.preventDefault();
            const formData = new FormData(this);
            fetch("/upload", {
                method: "POST",
                body: formData
            }).then(res => res.json())
              .then(data => {
                document.getElementById("result").innerText = data.message;
              });
        });

        // Handle chat messages
        document.getElementById("chatSend").addEventListener("click", function(){
            const message = document.getElementById("chatInput").value;
            if (!message) return;
            const chatBox = document.getElementById("chatBox");
            chatBox.innerHTML += `<div><b>You:</b> ${message}</div>`;
            fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message })
            }).then(res => res.json())
              .then(data => {
                chatBox.innerHTML += `<div><b>Bot:</b> ${data.message}</div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
              });
            document.getElementById("chatInput").value = "";
        });
    </script>
</body>
</html>
"""

# --- Routes ---
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, logo_base64=logo_base64)

@app.route("/upload", methods=["POST"])
def upload_image():
    global last_result
    if "file" in request.files:
        file = request.files["file"]
        if file.filename != "":
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

# --- Run ---
if __name__ == "__main__":
    app.run()

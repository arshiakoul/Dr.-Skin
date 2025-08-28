from flask import Flask, request, render_template_string, jsonify 
from skin_cancer_backend import predict, generate_gpt_response
import os
import base64

# NGROK import
from pyngrok import ngrok

app = Flask(__name__)
last_result = "No current detection"

# Load SVG logo and encode as Base64
with open("logo.svg", "rb") as f:
    logo_base64 = base64.b64encode(f.read()).decode("utf-8")

# --- HTML_TEMPLATE unchanged ---
HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Doctor Skin</title>
    <link href="https://fonts.googleapis.com/css2?family=Satoshi:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --p1: #d2d6fa;
            --p2: #a1adf5;
            --p3: #6c84f0;
            --p4: #305cde;
            --p5: #1e3d9a;
            --p6: #0d215a;
            --p7: #040e30;
        }}
        body {{
            font-family: 'Satoshi', sans-serif;
            margin: 0;
            padding: 0;
            background: var(--p1);
            display: flex;
            justify-content: center;
        }}
        .container {{
            width: 95vw;
            height: 90vh;
            margin: 5vh auto;
            display: flex;
            flex-direction: column;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            background: var(--p2);
        }}
        header {{
            display: flex;
            align-items: center;
            padding: 15px 20px;
            background: var(--p4);
            color: white;
            gap: 15px;
        }}
        header img {{
            height: 70px;
        }}
        header h1 {{
            font-size: 2em;
            margin: 0;
            font-weight: 600;
        }}
        .chat-box {{
            flex: 1;
            padding: 15px;
            background: var(--p1);
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 100%;
        }}
        .message {{
            max-width: 70%;
            padding: 15px 15px;
            border-radius: 20px;
            word-wrap: break-word;
            display: flex;
            align-items: center;
            position: relative;
            overflow-wrap: break-word;
        }}
        .user {{
            background: var(--p3);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 0;
        }}
        .bot {{
            background: var(--p4);
            color: white;
            align-self: flex-start;
            border-bottom-left-radius: 0;
            padding-left: 80px;
        }}
        .bot span {{
            display: block;
        }}
        .bot-logo {{
            position: absolute;
            left: 5px;
            width: 70px;
            height: 70px;
            border-radius: 50%;
            background: white;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }}
        .bot-logo img {{
            width: 90%;
            height: 90%;
        }}
        input[type=file], input[type=text] {{
            width: calc(100% - 30px);
            margin: 5px 15px;
            padding: 10px 15px;
            border-radius: 25px;
            border: 1px solid var(--p3);
            font-size: 1em;
            outline: none;
        }}
        button {{
            margin: 5px 15px;
            padding: 10px;
            border-radius: 25px;
            border: none;
            background: var(--p5);
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }}
        button:hover {{
            background: var(--p6);
            transform: scale(1.05);
        }}
        .loading {{
            font-style: italic;
            animation: dots 1s steps(4, end) infinite;
        }}
        @keyframes dots {{
            0%, 20% {{ content: ""; }}
            40% {{ content: "."; }}
            60% {{ content: ".."; }}
            80%, 100% {{ content: "..."; }}
        }}
        .image-preview {{
            display: none;
            max-width: 90%;
            margin: 10px auto;
            border-radius: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }}
        @media (max-width: 700px) {{
            .container {{
                margin: 10px;
                border-radius: 15px;
            }}
            header img {{
                height: 50px;
            }}
            header h1 {{
                font-size: 1.5em;
            }}
            .bot-logo {{
                left: 0px;
                width: 60px;
                height: 60px;
            }}
            .bot {{
                padding-left: 70px;
            }}
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <img src="data:image/svg+xml;base64,{logo_base64}" alt="Logo">
        <h1>Doctor Skin</h1>
    </header>

    <div class="chat-box" id="chatBox"></div>

    <input type="file" id="imageInput">
    <button onclick="uploadImage()">Analyze Image</button>
    <button onclick="toggleImage()" id="toggleBtn" style="display:none;">Show Image</button>
    <img id="imagePreview" class="image-preview">

    <input type="text" id="chatInput" placeholder="Ask a question...">
    <button onclick="sendMessage()">Send</button>
</div>

<script>
let lastImageData = null;
let imageVisible = false;

function addMessage(message, sender, isLoading=false) {{
    const chatBox = document.getElementById("chatBox");
    const msgDiv = document.createElement("div");
    msgDiv.className = 'message ' + sender;

    if(sender === 'bot') {{
        const logoDiv = document.createElement("div");
        logoDiv.className = "bot-logo";
        const logoImg = document.createElement("img");
        logoImg.src = "data:image/svg+xml;base64,{logo_base64}";
        logoDiv.appendChild(logoImg);
        msgDiv.appendChild(logoDiv);
    }}

    const textSpan = document.createElement("span");
    if(isLoading) {{
        textSpan.classList.add('loading');
        textSpan.innerText = "Thinking";
    }} else {{
        textSpan.innerText = message;
    }}
    msgDiv.appendChild(textSpan);

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msgDiv;
}}

function sendMessage() {{
    const input = document.getElementById("chatInput");
    const message = input.value;
    if (!message) return;
    addMessage(message, "user");
    input.value = "";

    const loadingDiv = addMessage("", "bot", true);

    fetch("/chat", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ message: message }})
    }})
    .then(res => res.json())
    .then(data => {{
        loadingDiv.remove();
        addMessage(data.message, "bot");
    }});
}}

function toggleImage() {{
    const preview = document.getElementById("imagePreview");
    imageVisible = !imageVisible;
    preview.style.display = imageVisible ? "block" : "none";
    document.getElementById("toggleBtn").innerText = imageVisible ? "Hide Image" : "Show Image";
}}

function uploadImage() {{
    const input = document.getElementById("imageInput");
    if (input.files.length === 0) return;

    lastImageData = input.files[0];
    const loadingDiv = addMessage("", "bot", true);

    const formData = new FormData();
    formData.append("file", input.files[0]);

    fetch("/upload", {{ method: "POST", body: formData }})
    .then(res => res.json())
    .then(data => {{
        loadingDiv.remove();
        addMessage(data.message, "bot");

        const preview = document.getElementById("imagePreview");
        preview.src = URL.createObjectURL(lastImageData);
        document.getElementById("toggleBtn").style.display = "block";
        imageVisible = true;
        preview.style.display = "block";
        document.getElementById("toggleBtn").innerText = "Hide Image";
    }});
}}
</script>
</body>
</html>
"""
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # use env port if available

    # Start ngrok tunnel
    public_url = ngrok.connect(port)
    print(f" * ngrok tunnel available at: {public_url}")

    # Start Flask app
    app.run(host="0.0.0.0", port=port, debug=True)

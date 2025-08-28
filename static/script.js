function addMessage(message, sender) {
    const chatBox = document.getElementById("chatBox");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;
    msgDiv.innerText = message;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById("chatInput");
    const message = input.value;
    if (!message) return;
    addMessage(message, "user");
    input.value = "";

    fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message })
    })
    .then(res => res.json())
    .then(data => addMessage(data.message, "bot"));
}

function uploadImage() {
    const input = document.getElementById("imageInput");
    if (input.files.length === 0) return;
    const formData = new FormData();
    formData.append("file", input.files[0]);

    fetch("/upload", { method: "POST", body: formData })
    .then(res => res.json())
    .then(data => addMessage(data.message, "bot"));
}

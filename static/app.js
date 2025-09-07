const form = document.getElementById("chat-form");
const messages = document.getElementById("messages");
const chatInput = document.getElementById("chatInput");

function appendMessage(role, text) {
    const msg = document.createElement("article");
    msg.className = `msg ${role}`;
    msg.innerHTML = `
    <div class="avatar">${role === "user" ? "U" : "AI"}</div>
    <div class="bubble">
      <div class="meta">${role === "user" ? "You" : "Assistant"} • just now</div>
      ${text}
    </div>
  `;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
   
    const userMsg = chatInput.value.trim();
    if (!userMsg) return;

    appendMessage("user", userMsg);

    chatInput.value = "";
    console.log(userMsg);

    try {

        const formData = new FormData();
        formData.append("message", userMsg);
        const res = await fetch("/chat", {
            method: "POST",
            body: formData,
        });

        const data = await res.json();
        console.log(data || JSON.stringify(data));
        appendMessage("bot", data.answer || JSON.stringify(data));
       
    } catch (err) {
        appendMessage("bot", "⚠️ Error: " + err.message);
    }
});

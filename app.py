from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Serve a simple chat UI
@app.get("/", response_class=HTMLResponse)
def get_ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI Chat</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            #chat-box { border: 1px solid #ccc; padding: 10px; width: 300px; height: 300px; overflow-y: auto; }
            #input-box { margin-top: 10px; }
        </style>
    </head>
    <body>
        <h2>FastAPI Chat</h2>
        <div id="chat-box"></div>
        <div id="input-box">
            <input type="text" id="message" placeholder="Type a message" />
            <button onclick="sendMessage()">Send</button>
        </div>
        <script>
            async function sendMessage() {
                let msg = document.getElementById("message").value;
                if (!msg) return;
                document.getElementById("chat-box").innerHTML += "<div><b>You:</b> " + msg + "</div>";
                document.getElementById("message").value = "";
                let response = await fetch("/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: msg })
                });
                let data = await response.json();
                document.getElementById("chat-box").innerHTML += "<div><b>Bot:</b> " + data.reply + "</div>";
            }
        </script>
    </body>
    </html>
    """

# Simple chat backend
@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message", "")
    return JSONResponse({"reply": f"You said: {user_message}"})

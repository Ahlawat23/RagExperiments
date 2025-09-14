import {userState, useState} from "react";
import {Send} from "lucide-react";
import './style/input.css'

export  function ChatInput({onSendMessage}){
    const [message, setMessage] = useState("");

    const handleSubmit = (e) => {
        
        e.preventDefault();
        
        if(message.trim()){
            onSendMessage(message);
            setMessage("");
        }
    }

    return(
        <>
        <div class="lower-section">
            <form class="chat-input" onSubmit={handleSubmit}>
                <input type="text" placeholder="Ask anything" value={message} onChange={(e) => setMessage(e.target.value)}/>
                <button type="submit" class="submit"><Send /> </button>
            </form>
        </div>
       
        </>
    );
}
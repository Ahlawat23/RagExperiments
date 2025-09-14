import { User, Bot } from "lucide-react";
import './style/message.css'

export function MessageUI({message, isUser, timestamp}){
    return(
        <>
        <div class="messageBox">
            <div class="message-text">{message}</div>
            <div class="message-timestamp">{timestamp}</div>
        </div>
        </>
    );
}
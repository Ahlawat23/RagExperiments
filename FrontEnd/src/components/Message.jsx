import { User, Bot } from "lucide-react";
import './style/message.css'

export function MessageUI({message, isUser, timestamp}){
    return(
        <>
        {isUser? ( // USER
        <div class="user-message">
            <div class="message-text">{message}</div>
        </div>

        ):( //AI RESPONSE
        <div class="bot-message">
            <div class="bot-text">{message}</div>
        </div>
        )} 
        </>
    );
}
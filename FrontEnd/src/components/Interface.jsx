import './style/interface.css'
import { RefreshCw, Sparkles } from "lucide-react";


export function LoadInterface(){
    return (
    <>
     {/* -- Header -- */}
    <div class="header">
        <div class="header-left"> 
            <Sparkles /> <h3>. . Chatter</h3>
        </div>
        <div class="header-right">
             <button class="new-chat-button"> <RefreshCw /> New chat</button>
        </div>
    </div>
    <div class="chat-container">
    
       
    </div>
    <div class="lower-section">
        <div class="chat-input">
            <input type="text" placeholder="Ask anything" />
        </div>
    </div>
    </>
    );
}
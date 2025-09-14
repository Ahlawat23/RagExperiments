import { useState, useRef, useEffect } from "react";
import './style/interface.css'
import { RefreshCw, Sparkles } from "lucide-react";
import {ChatInput} from "./Input.jsx";
import {MessageUI} from "./Message.jsx";


const initialMessages = [
  {
    id: 1,
    text: "Hello! I'm ChatGPT running in Windows Vista style. How can I help you today?",
    isUser: false,
    timestamp: new Date().toLocaleTimeString(),
  },
];

export function LoadInterface(){
    const [messages, setMessages] = useState(initialMessages);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);


    const handleSendMessage = (text) => {
        const newMessage = {
            id: messages.length + 1,
            text,
            isUser: true,
            timestamp: new Date().toLocaleTimeString(),
        };

        setMessages((prev) => [...prev, newMessage]);

        setTimeout(() => {
            const response = {
                id: messages.length + 2,
                text: text,
                isUser: false,
                timestamp: new Date().toLocaleTimeString(),
            };
        setMessages((prev) => [...prev, response]);}, 1000);
    };


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
        {messages.map((message) => (
            <MessageUI
              key={message.id}
              message={message.text}
              isUser={message.isUser}
              timestamp={message.timestamp}
            />
          ))}
          <div ref={messagesEndRef} />
    </div>
    <ChatInput onSendMessage={handleSendMessage}/>
    </>
    );
}
import { useState } from 'react'
import './App.css'
import ChatInterface from "./components/chatInterface";


function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="h-screen w-screen overflow-hidden">
      <ChatInterface />
    </div>
  );
  
}

export default App

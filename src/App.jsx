import { useState } from 'react'
import './App.css'
import ChatInterface from "./components/chatInterface";


function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="flex h-full w-full flex-col">
      <ChatInterface />
    </div>
  );
  
}

export default App

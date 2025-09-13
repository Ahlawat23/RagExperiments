import { useState } from 'react'
import './App.css'
import ChatInterface from "./components/chatInterface";


function App() {
  const [count, setCount] = useState(0)

  return (
      <ChatInterface />
  );
  
}

export default App

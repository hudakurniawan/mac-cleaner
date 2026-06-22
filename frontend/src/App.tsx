import { useState } from 'react'
import './App.css'
import SpaceLens from './components/SpaceLens'

function App() {
  return (
    <div className="app-container" style={{ minHeight: '100vh', padding: '2rem', background: '#121212', color: '#fff' }}>
      <header style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '3rem', fontWeight: 'bold', background: 'linear-gradient(to right, #60a5fa, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          SmartClean macOS
        </h1>
        <p style={{ opacity: 0.8 }}>Premium macOS Optimization Suite</p>
      </header>

      <main style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <SpaceLens />
      </main>
    </div>
  )
}

export default App

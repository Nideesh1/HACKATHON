import { Routes, Route, NavLink } from 'react-router-dom'
import Documents from './pages/Documents'
import Dashboard from './pages/Dashboard'
import './App.css'

function App() {
  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">
          <span className="brand-icon">C</span>
          <span className="brand-text">CLAIMS RAG</span>
        </div>
        <div className="nav-links">
          <NavLink to="/documents" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Documents
          </NavLink>
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            Dashboard
          </NavLink>
        </div>
      </nav>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  )
}

export default App

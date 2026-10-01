import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axiosInstance } from './services/api';

import Dashboard from './pages/Dashboard';
import PapersList from './pages/PapersList';
import PaperDetail from './pages/PaperDetail';
import ProjectsList from './pages/ProjectsList';
import ProjectDetail from './pages/ProjectDetail';
import SearchPage from './pages/SearchPage';
import About from './pages/About';

const queryClient = new QueryClient();

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <nav className="navbar">
          <div className="navbar-brand">
            <span className="navbar-icon">🔬</span>
            <span className="navbar-title">QuantumHub</span>
          </div>
          <ul className="navbar-nav">
            <li className="nav-item">
              <a className="nav-link" to="/">Dashboard</a>
            </li>
            <li className="nav-item">
              <a className="nav-link" to="/papers">Papers</a>
            </li>
            <li className="nav-item">
              <a className="nav-link" to="/projects">Projects</a>
            </li>
            <li className="nav-item">
              <a className="nav-link" to="/search">Search</a>
            </li>
            <li className="nav-item">
              <a className="nav-link" to="/about">About</a>
            </li>
          </ul>
        </nav>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/papers" element={<PapersList />} />
          <Route path="/papers/:id" element={<PaperDetail />} />
          <Route path="/projects" element={<ProjectsList />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
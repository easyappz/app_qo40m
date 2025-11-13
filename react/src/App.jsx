import React, { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import ErrorBoundary from './ErrorBoundary';
import './App.css';

import { Home } from './components/Home';
import MainLayout from './components/Layout/MainLayout';
import NotFound from './components/NotFound';
import { Register } from './components/Auth/Register';
import { Login } from './components/Auth/Login';
import { Ad } from './components/Ad';
import { Profile } from './components/Profile';

function App() {
  /** Никогда не удаляй этот код */
  useEffect(() => {
    if (typeof window !== 'undefined' && typeof window.handleRoutes === 'function') {
      /** Нужно передавать список существующих роутов */
      window.handleRoutes(['/', '/register', '/login', '/ad/:id', '/profile']);
    }
  }, []);

  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<MainLayout />}> 
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />
          <Route path="/ad/:id" element={<Ad />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  );
}

export default App;

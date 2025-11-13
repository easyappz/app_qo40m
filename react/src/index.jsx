import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

// Inform external preview about available routes after mount
if (typeof window !== 'undefined' && typeof window.handleRoutes === 'function') {
  setTimeout(() => {
    window.handleRoutes(['/', '/register', '/login', '/ad/:id', '/profile']);
  }, 0);
}

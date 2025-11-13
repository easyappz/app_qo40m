import React from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';

const MainLayout = () => {
  const navigate = useNavigate();
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;

  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('token');
      window.localStorage.removeItem('refreshToken');
    }
    navigate('/login');
  };

  return (
    <div className="app-shell" data-easytag="id1-src/components/Layout/MainLayout.jsx">
      <header className="header">
        <div className="container header-inner">
          <Link to="/" className="logo" aria-label="Авитолог — на главную">Авитолог</Link>
          <nav className="nav">
            <NavLink to="/" className="nav-link">Главная</NavLink>
            <NavLink to="/profile" className="nav-link">Профиль</NavLink>
            {token ? (
              <button type="button" className="btn btn-link" onClick={handleLogout} data-easytag="id2-src/components/Layout/MainLayout.jsx">Выйти</button>
            ) : (
              <NavLink to="/login" className="nav-link">Войти</NavLink>
            )}
          </nav>
        </div>
      </header>

      <main className="main">
        <div className="container">
          <Outlet />
        </div>
      </main>

      <footer className="footer">
        <div className="container footer-inner">
          <span className="muted">© {new Date().getFullYear()} Авитолог</span>
          <div className="muted">Сервис обсуждения объявлений</div>
        </div>
      </footer>
    </div>
  );
};

export default MainLayout;

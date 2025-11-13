import React from 'react';
import { Link } from 'react-router-dom';

export const Login = () => {
  return (
    <section className="card" data-easytag="id1-src/components/Auth/Login.jsx">
      <h1 className="h1">Вход</h1>
      <p className="muted">Форма авторизации будет здесь.</p>
      <div className="actions">
        <Link to="/register" className="btn btn-secondary">Создать аккаунт</Link>
      </div>
    </section>
  );
};

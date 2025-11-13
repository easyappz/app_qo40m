import React from 'react';
import { Link } from 'react-router-dom';

export const Register = () => {
  return (
    <section className="card" data-easytag="id1-src/components/Auth/Register.jsx">
      <h1 className="h1">Регистрация</h1>
      <p className="muted">Форма регистрации будет здесь.</p>
      <div className="actions">
        <Link to="/login" className="btn btn-secondary">У меня уже есть аккаунт</Link>
      </div>
    </section>
  );
};

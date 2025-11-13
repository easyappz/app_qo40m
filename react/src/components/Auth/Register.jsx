import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { register as apiRegister } from '../../api/auth.jsx';

export const Register = () => {
  const navigate = useNavigate();

  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiRegister({ username: form.username.trim(), email: form.email.trim(), password: form.password });
      navigate('/login', { state: { justRegistered: true } });
    } catch (err) {
      setError(err.message || 'Произошла ошибка. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card" data-easytag="id1-src/components/Auth/Register.jsx">
      <h1 className="h1">Регистрация</h1>
      <p className="muted">Создайте аккаунт, чтобы участвовать в обсуждениях объявлений.</p>

      <form className="form" onSubmit={onSubmit} noValidate data-easytag="id2-src/components/Auth/Register.jsx">
        <div className="form-row">
          <label htmlFor="username">Имя пользователя</label>
          <input
            id="username"
            name="username"
            type="text"
            className="input"
            placeholder="Введите имя пользователя"
            value={form.username}
            onChange={onChange}
            required
            autoComplete="username"
          />
        </div>

        <div className="form-row">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            name="email"
            type="email"
            className="input"
            placeholder="you@example.com"
            value={form.email}
            onChange={onChange}
            required
            autoComplete="email"
          />
        </div>

        <div className="form-row">
          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            name="password"
            type="password"
            className="input"
            placeholder="Введите пароль"
            value={form.password}
            onChange={onChange}
            required
            autoComplete="new-password"
            minLength={6}
          />
        </div>

        {error ? <div className="error" role="alert">{error}</div> : null}

        <div className="actions">
          <button
            type="submit"
            className="btn"
            disabled={loading}
            data-easytag="id3-src/components/Auth/Register.jsx"
          >
            {loading ? 'Создание…' : 'Зарегистрироваться'}
          </button>
          <Link to="/login" className="btn btn-secondary" data-easytag="id4-src/components/Auth/Register.jsx">У меня уже есть аккаунт</Link>
        </div>
      </form>
    </section>
  );
};

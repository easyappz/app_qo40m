import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { login as apiLogin } from '../../api/auth.jsx';

export const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({ username_or_email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const justRegistered = Boolean(location.state && location.state.justRegistered);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiLogin({ username_or_email: form.username_or_email.trim(), password: form.password });
      if (data && data.access && data.refresh) {
        localStorage.setItem('token', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        navigate('/profile');
      } else {
        setError('Неверный ответ сервера.');
      }
    } catch (err) {
      setError(err.message || 'Неверные учетные данные');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card" data-easytag="id1-src/components/Auth/Login.jsx">
      <h1 className="h1">Вход</h1>
      {justRegistered ? (
        <div className="success" role="status">Регистрация прошла успешно. Введите данные для входа.</div>
      ) : null}
      <form className="form" onSubmit={onSubmit} noValidate data-easytag="id2-src/components/Auth/Login.jsx">
        <div className="form-row">
          <label htmlFor="username_or_email">Имя пользователя или Email</label>
          <input
            id="username_or_email"
            name="username_or_email"
            type="text"
            className="input"
            placeholder="username или you@example.com"
            value={form.username_or_email}
            onChange={onChange}
            required
            autoComplete="username"
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
            autoComplete="current-password"
          />
        </div>

        {error ? <div className="error" role="alert">{error}</div> : null}

        <div className="actions">
          <button type="submit" className="btn" disabled={loading} data-easytag="id3-src/components/Auth/Login.jsx">
            {loading ? 'Вход…' : 'Войти'}
          </button>
          <Link to="/register" className="btn btn-secondary" data-easytag="id4-src/components/Auth/Login.jsx">Создать аккаунт</Link>
        </div>
      </form>
    </section>
  );
};

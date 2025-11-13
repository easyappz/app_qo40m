import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getMe } from '../../api/auth.jsx';

export const Profile = () => {
  const navigate = useNavigate();
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;

  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [me, setMe] = useState(null);

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    setLoading(true);
    getMe()
      .then((data) => {
        if (mounted) setMe(data);
      })
      .catch((err) => {
        setError(err.message || 'Ошибка загрузки профиля');
      })
      .finally(() => setLoading(false));
    return () => {
      mounted = false;
    };
  }, [token]);

  const handleLogout = () => {
    try {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
    } catch (_) {
      // no-op
    }
    navigate('/');
  };

  if (!token) {
    return (
      <section className="card" data-easytag="id1-src/components/Profile/index.jsx">
        <h1 className="h1">Профиль</h1>
        <p className="muted">Для доступа к профилю войдите в систему.</p>
        <div className="actions">
          <Link to="/login" className="btn" data-easytag="id2-src/components/Profile/index.jsx">Войти</Link>
          <Link to="/register" className="btn btn-secondary" data-easytag="id3-src/components/Profile/index.jsx">Создать аккаунт</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="card" data-easytag="id1-src/components/Profile/index.jsx">
      <div className="profile-header">
        <h1 className="h1">Профиль</h1>
        <button type="button" className="btn btn-secondary" onClick={handleLogout} data-easytag="id4-src/components/Profile/index.jsx">Выйти</button>
      </div>

      {loading ? <div className="muted">Загрузка…</div> : null}
      {error ? <div className="error" role="alert">{error}</div> : null}

      <div className="tabs">
        <button
          type="button"
          className={`tab ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
          data-easytag="id5-src/components/Profile/index.jsx"
        >
          Профиль
        </button>
        <button
          type="button"
          className={`tab ${activeTab === 'my_ads' ? 'active' : ''}`}
          onClick={() => setActiveTab('my_ads')}
          data-easytag="id6-src/components/Profile/index.jsx"
        >
          Мои объявления
        </button>
        <button
          type="button"
          className={`tab ${activeTab === 'favorites' ? 'active' : ''}`}
          onClick={() => setActiveTab('favorites')}
          data-easytag="id7-src/components/Profile/index.jsx"
        >
          Избранное
        </button>
        <button
          type="button"
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
          data-easytag="id8-src/components/Profile/index.jsx"
        >
          История
        </button>
      </div>

      <div className="tab-panels">
        {activeTab === 'profile' && (
          <div className="panel">
            {me ? (
              <div className="grid">
                <div><span className="muted">Имя пользователя:</span> {me.username}</div>
                <div><span className="muted">Email:</span> {me.email}</div>
                <div><span className="muted">Зарегистрирован:</span> {new Date(me.created_at).toLocaleString()}</div>
              </div>
            ) : (
              <div className="muted">Нет данных профиля.</div>
            )}
          </div>
        )}

        {activeTab === 'my_ads' && (
          <div className="panel">
            <div className="muted">Ваши объявления появятся здесь.</div>
          </div>
        )}

        {activeTab === 'favorites' && (
          <div className="panel">
            <div className="muted">Избранные объявления появятся здесь.</div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="panel">
            <div className="muted">История просмотров появится здесь.</div>
          </div>
        )}
      </div>
    </section>
  );
};

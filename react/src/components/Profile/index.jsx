import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getMe, updateMe } from '../../api/auth.jsx';
import { getMyAds, getMyFavorites } from '../../api/ads.jsx';
import { getMyHistory } from '../../api/history.jsx';

function formatPriceRub(minor) {
  if (typeof minor !== 'number' || Number.isNaN(minor)) return '—';
  const rub = minor / 100;
  try {
    return rub.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
  } catch (_) {
    return `${Math.round(rub)} ₽`;
  }
}

export const Profile = () => {
  const navigate = useNavigate();
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;

  const [activeTab, setActiveTab] = useState('profile');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [me, setMe] = useState(null);

  const [form, setForm] = useState({ username: '', avatar_url: '' });
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState('');

  const [myAds, setMyAds] = useState([]);
  const [myAdsError, setMyAdsError] = useState('');
  const [favorites, setFavorites] = useState([]);
  const [favoritesError, setFavoritesError] = useState('');
  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState('');

  useEffect(() => {
    if (!token) return;
    let mounted = true;
    setLoading(true);
    getMe()
      .then((data) => {
        if (!mounted) return;
        setMe(data);
        setForm({ username: data.username || '', avatar_url: data.avatar_url || '' });
      })
      .catch((err) => setError(err.message || 'Ошибка загрузки профиля'))
      .finally(() => setLoading(false));
    return () => {
      mounted = false;
    };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    if (activeTab === 'my_ads') {
      getMyAds().then(setMyAds).catch((e) => setMyAdsError(e.message || 'Не удалось загрузить')).finally(() => {});
    }
    if (activeTab === 'favorites') {
      getMyFavorites().then(setFavorites).catch((e) => setFavoritesError(e.message || 'Не удалось загрузить')).finally(() => {});
    }
    if (activeTab === 'history') {
      getMyHistory().then((d) => setHistory(Array.isArray(d.items) ? d.items : [])).catch((e) => setHistoryError(e.message || 'Не удалось загрузить')).finally(() => {});
    }
  }, [activeTab, token]);

  const onSave = async (e) => {
    e.preventDefault();
    setSaveError('');
    setSaveSuccess('');
    setSaveLoading(true);
    try {
      const updated = await updateMe({ username: form.username.trim(), avatar_url: form.avatar_url.trim() });
      setMe(updated);
      setSaveSuccess('Профиль обновлен');
    } catch (err) {
      setSaveError(err.message || 'Не удалось сохранить изменения');
    } finally {
      setSaveLoading(false);
    }
  };

  const handleLogout = () => {
    try {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
    } catch (_) {}
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
        <button type="button" className={`tab ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => setActiveTab('profile')} data-easytag="id5-src/components/Profile/index.jsx">Профиль</button>
        <button type="button" className={`tab ${activeTab === 'my_ads' ? 'active' : ''}`} onClick={() => setActiveTab('my_ads')} data-easytag="id6-src/components/Profile/index.jsx">Мои объявления</button>
        <button type="button" className={`tab ${activeTab === 'favorites' ? 'active' : ''}`} onClick={() => setActiveTab('favorites')} data-easytag="id7-src/components/Profile/index.jsx">Избранное</button>
        <button type="button" className={`tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')} data-easytag="id8-src/components/Profile/index.jsx">История</button>
      </div>

      <div className="tab-panels">
        {activeTab === 'profile' && (
          <div className="panel" data-easytag="id9-src/components/Profile/index.jsx">
            {me ? (
              <form className="form" onSubmit={onSave} noValidate data-easytag="id10-src/components/Profile/index.jsx">
                <div className="form-row">
                  <label htmlFor="username">Имя пользователя</label>
                  <input id="username" className="input" value={form.username} onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))} data-easytag="id11-src/components/Profile/index.jsx" />
                </div>
                <div className="form-row">
                  <label htmlFor="avatar_url">Ссылка на аватар</label>
                  <input id="avatar_url" className="input" value={form.avatar_url} onChange={(e) => setForm((p) => ({ ...p, avatar_url: e.target.value }))} data-easytag="id12-src/components/Profile/index.jsx" />
                </div>
                {saveError ? <div className="error" role="alert">{saveError}</div> : null}
                {saveSuccess ? <div className="success" role="status">{saveSuccess}</div> : null}
                <div className="actions">
                  <button type="submit" className="btn" disabled={saveLoading} data-easytag="id13-src/components/Profile/index.jsx">{saveLoading ? 'Сохранение…' : 'Сохранить'}</button>
                </div>
              </form>
            ) : (
              <div className="muted">Нет данных профиля.</div>
            )}
          </div>
        )}

        {activeTab === 'my_ads' && (
          <div className="panel" data-easytag="id14-src/components/Profile/index.jsx">
            {myAdsError ? <div className="error" role="alert">{myAdsError}</div> : null}
            <div className="grid-cards">
              {myAds.map((ad) => (
                <button key={ad.id} type="button" className="ad-card" onClick={() => navigate(`/ad/${ad.id}`)} data-easytag="id15-src/components/Profile/index.jsx">
                  <div className="ad-card-cover">{ad.cover ? <img src={ad.cover} alt="" /> : <div className="ad-card-placeholder" />}</div>
                  <div className="ad-card-body">
                    <div className="ad-card-title">{ad.title}</div>
                    <div className="ad-card-price">{formatPriceRub(ad.price)}</div>
                    <div className="ad-card-meta">
                      <span>★ {Number(ad.avg_rating || 0).toFixed(1)}</span>
                      <span>👁 {ad.views_count}</span>
                      <span>💬 {ad.comments_count}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'favorites' && (
          <div className="panel" data-easytag="id16-src/components/Profile/index.jsx">
            {favoritesError ? <div className="error" role="alert">{favoritesError}</div> : null}
            <div className="grid-cards">
              {favorites.map((ad) => (
                <button key={ad.id} type="button" className="ad-card" onClick={() => navigate(`/ad/${ad.id}`)} data-easytag="id17-src/components/Profile/index.jsx">
                  <div className="ad-card-cover">{ad.cover ? <img src={ad.cover} alt="" /> : <div className="ad-card-placeholder" />}</div>
                  <div className="ad-card-body">
                    <div className="ad-card-title">{ad.title}</div>
                    <div className="ad-card-price">{formatPriceRub(ad.price)}</div>
                    <div className="ad-card-meta">
                      <span>★ {Number(ad.avg_rating || 0).toFixed(1)}</span>
                      <span>👁 {ad.views_count}</span>
                      <span>💬 {ad.comments_count}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="panel" data-easytag="id18-src/components/Profile/index.jsx">
            {historyError ? <div className="error" role="alert">{historyError}</div> : null}
            <div className="grid-cards">
              {history.map((h, idx) => (
                <button key={idx} type="button" className="ad-card" onClick={() => navigate(`/ad/${h.ad.id}`)} data-easytag="id19-src/components/Profile/index.jsx">
                  <div className="ad-card-cover">{h.ad.cover ? <img src={h.ad.cover} alt="" /> : <div className="ad-card-placeholder" />}</div>
                  <div className="ad-card-body">
                    <div className="ad-card-title">{h.ad.title}</div>
                    <div className="ad-card-price">{formatPriceRub(h.ad.price)}</div>
                    <div className="ad-card-meta">
                      <span>★ {Number(h.ad.avg_rating || 0).toFixed(1)}</span>
                      <span>👁 {h.ad.views_count}</span>
                      <span>💬 {h.ad.comments_count}</span>
                      <span className="muted small">{new Date(h.viewed_at).toLocaleString()}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

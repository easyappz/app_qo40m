import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { importFromAvito, getPopular } from '../../api/ads.jsx';

function formatPriceRub(minor) {
  if (typeof minor !== 'number' || Number.isNaN(minor)) return '—';
  const rub = minor / 100;
  try {
    return rub.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
  } catch (_) {
    return `${Math.round(rub)} ₽`;
  }
}

export const Home = () => {
  const navigate = useNavigate();

  const [url, setUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState('');

  const [popular, setPopular] = useState([]);
  const [nextOffset, setNextOffset] = useState(null);
  const [loadingPopular, setLoadingPopular] = useState(false);
  const [popularError, setPopularError] = useState('');

  useEffect(() => {
    let mounted = true;
    setLoadingPopular(true);
    getPopular({ limit: 20, offset: 0 })
      .then((data) => {
        if (!mounted) return;
        setPopular(Array.isArray(data.items) ? data.items : []);
        setNextOffset(data.next_offset ?? null);
      })
      .catch((err) => setPopularError(err.message || 'Не удалось загрузить популярные объявления'))
      .finally(() => setLoadingPopular(false));
    return () => {
      mounted = false;
    };
  }, []);

  const onSubmit = async (e) => {
    e.preventDefault();
    setImportError('');
    const trimmed = url.trim();
    if (!trimmed) {
      setImportError('Введите ссылку на объявление.');
      return;
    }
    setImporting(true);
    try {
      const ad = await importFromAvito(trimmed);
      if (ad && ad.id) {
        navigate(`/ad/${ad.id}`);
      } else {
        setImportError('Сервер вернул неожиданный ответ.');
      }
    } catch (err) {
      setImportError(err.message || 'Ошибка импорта объявления.');
    } finally {
      setImporting(false);
    }
  };

  const loadMore = async () => {
    if (nextOffset === null || loadingPopular) return;
    setLoadingPopular(true);
    try {
      const data = await getPopular({ limit: 20, offset: nextOffset });
      setPopular((prev) => prev.concat(Array.isArray(data.items) ? data.items : []));
      setNextOffset(data.next_offset ?? null);
    } catch (err) {
      setPopularError(err.message || 'Ошибка загрузки ленты.');
    } finally {
      setLoadingPopular(false);
    }
  };

  return (
    <section className="home" data-easytag="id1-src/components/Home/index.jsx">
      <div className="card" style={{ marginBottom: 16 }} data-easytag="id2-src/components/Home/index.jsx">
        <h1 className="h1">Обсуждайте объявления с Авито</h1>
        <p className="muted">Вставьте ссылку на объявление, чтобы создать обсуждение.</p>
        <form className="hero-actions" onSubmit={onSubmit} noValidate data-easytag="id3-src/components/Home/index.jsx">
          <input
            type="url"
            className="input"
            placeholder="Ссылка на объявление Авито"
            aria-label="Ссылка на объявление с Авито"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            data-easytag="id4-src/components/Home/index.jsx"
          />
          <button type="submit" className="btn" disabled={importing} data-easytag="id5-src/components/Home/index.jsx">
            {importing ? 'Импорт…' : 'Импортировать'}
          </button>
        </form>
        {importError ? <div className="error" role="alert" data-easytag="id6-src/components/Home/index.jsx">{importError}</div> : null}
      </div>

      <div className="card" data-easytag="id7-src/components/Home/index.jsx">
        <div className="actions" style={{ justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>Популярные</h2>
          {loadingPopular ? <span className="muted small">Загрузка…</span> : null}
        </div>
        {popularError ? <div className="error" role="alert" data-easytag="id8-src/components/Home/index.jsx">{popularError}</div> : null}
        <div className="grid-cards" data-easytag="id9-src/components/Home/index.jsx">
          {popular.map((ad) => (
            <button
              key={ad.id}
              type="button"
              className="ad-card"
              onClick={() => navigate(`/ad/${ad.id}`)}
              aria-label={`Открыть объявление ${ad.title}`}
              data-easytag="id10-src/components/Home/index.jsx"
            >
              <div className="ad-card-cover">
                {ad.cover ? (
                  <img src={ad.cover} alt="" />
                ) : (
                  <div className="ad-card-placeholder" />
                )}
              </div>
              <div className="ad-card-body">
                <div className="ad-card-title" title={ad.title}>{ad.title}</div>
                <div className="ad-card-price">{formatPriceRub(ad.price)}</div>
                <div className="ad-card-meta">
                  <span title="Рейтинг">★ {Number(ad.avg_rating || 0).toFixed(1)}</span>
                  <span title="Просмотры">👁 {ad.views_count}</span>
                  <span title="Комментарии">💬 {ad.comments_count}</span>
                  <span title="Лайки">❤ {ad.likes_count}</span>
                </div>
              </div>
            </button>
          ))}
        </div>
        {nextOffset !== null ? (
          <div className="actions" style={{ justifyContent: 'center', marginTop: 8 }}>
            <button type="button" className="btn btn-secondary" onClick={loadMore} disabled={loadingPopular} data-easytag="id11-src/components/Home/index.jsx">
              {loadingPopular ? 'Загрузка…' : 'Загрузить ещё'}
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
};

export default Home;

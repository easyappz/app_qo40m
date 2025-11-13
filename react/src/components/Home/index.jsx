import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPopular } from '../../api/ads.jsx';
import { createImport, getImportStatus } from '../../api/imports.jsx';

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

  // Import workflow state
  const [url, setUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState('');
  const [cooldown, setCooldown] = useState(0); // seconds remaining for retry-after
  const pollRef = useRef(null);
  const cooldownRef = useRef(null);

  // Popular feed state
  const [popular, setPopular] = useState([]);
  const [nextOffset, setNextOffset] = useState(null);
  const [loadingPopular, setLoadingPopular] = useState(false);
  const [popularError, setPopularError] = useState('');

  // Helpers
  const clearPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startCooldown = (seconds) => {
    const secs = Number(seconds);
    if (!Number.isFinite(secs) || secs <= 0) return;
    if (cooldownRef.current) {
      clearInterval(cooldownRef.current);
      cooldownRef.current = null;
    }
    setCooldown(Math.ceil(secs));
    cooldownRef.current = setInterval(() => {
      setCooldown((s) => {
        if (s <= 1) {
          clearInterval(cooldownRef.current);
          cooldownRef.current = null;
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  };

  const beginPolling = (id) => {
    clearPolling();
    pollRef.current = setInterval(async () => {
      try {
        const { data: job } = await getImportStatus(id);
        if (!job || !job.status) return;
        if (job.status === 'done') {
          clearPolling();
          if (job.ad_id) {
            navigate(`/ad/${job.ad_id}`);
          } else {
            setImportError('Импорт завершён, но объявление не найдено.');
          }
        } else if (job.status === 'blocked') {
          clearPolling();
          if (job.retry_after) startCooldown(job.retry_after);
        } else if (job.status === 'error') {
          clearPolling();
          setImportError(job.message || 'Ошибка импорта.');
        }
        // if queued/processing -> keep polling
      } catch (e) {
        // Stop polling on hard error
        clearPolling();
        setImportError(e?.response?.data?.message || e?.message || 'Ошибка при получении статуса импорта.');
      }
    }, 2000);
  };

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

  useEffect(() => () => {
    clearPolling();
    if (cooldownRef.current) {
      clearInterval(cooldownRef.current);
      cooldownRef.current = null;
    }
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
      const response = await createImport(trimmed);
      const statusCode = response?.status;
      const job = response?.data || {};
      if (statusCode === 201 && job && job.id) {
        // Handle initial job state
        if (job.status === 'done') {
          if (job.ad_id) {
            navigate(`/ad/${job.ad_id}`);
          } else {
            setImportError('Импорт завершён, но объявление не найдено.');
          }
        } else if (job.status === 'blocked') {
          if (job.retry_after) startCooldown(job.retry_after);
        } else if (job.status === 'queued' || job.status === 'processing') {
          beginPolling(job.id);
        } else if (job.status === 'error') {
          setImportError(job.message || 'Ошибка импорта.');
        } else {
          setImportError('Сервер вернул неожиданный статус.');
        }
      } else {
        setImportError('Сервер вернул неожиданный ответ.');
      }
    } catch (err) {
      const status = err?.response?.status;
      if (status === 429) {
        const headerRetry = err?.response?.headers?.['retry-after'];
        const bodyRetry = err?.response?.data?.retry_after;
        const retryAfter = Number(headerRetry || bodyRetry || 0);
        if (Number.isFinite(retryAfter) && retryAfter > 0) {
          startCooldown(retryAfter);
          setImportError('');
        } else {
          setImportError('Слишком много запросов. Повторите позже.');
        }
      } else {
        const msg = err?.response?.data?.message || err?.response?.data?.detail || err?.message || 'Ошибка импорта объявления.';
        setImportError(msg);
      }
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

  const submitDisabled = importing || cooldown > 0;

  return (
    <section className="home" data-easytag="id1-src/components/Home/index.jsx" style={{ maxWidth: 880, margin: '0 auto', padding: 16 }}>
      <div className="card" style={{ marginBottom: 16 }} data-easytag="id2-src/components/Home/index.jsx">
        <h1 className="h1">Обсуждайте объявления с Авито</h1>
        <p className="muted">Вставьте ссылку на объявление, чтобы создать обсуждение.</p>
        <form className="hero-actions" onSubmit={onSubmit} noValidate data-easytag="id3-src/components/Home/index.jsx" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="url"
            className="input"
            placeholder="Ссылка на объявление Авито"
            aria-label="Ссылка на объявление с Авито"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            data-easytag="id4-src/components/Home/index.jsx"
            style={{ flex: 1, minWidth: 0 }}
          />
          <button
            type="submit"
            className="btn"
            aria-busy={importing ? 'true' : 'false'}
            aria-disabled={submitDisabled ? 'true' : 'false'}
            disabled={submitDisabled}
            data-easytag="id5-src/components/Home/index.jsx"
            style={{ minWidth: 140, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
          >
            {importing ? (
              <>
                <svg width="16" height="16" viewBox="0 0 50 50" aria-hidden="true">
                  <circle cx="25" cy="25" r="20" stroke="currentColor" strokeWidth="6" fill="none" strokeLinecap="round">
                    <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="0.8s" repeatCount="indefinite" />
                  </circle>
                </svg>
                Импорт…
              </>
            ) : (
              'Импортировать'
            )}
          </button>
        </form>
        {cooldown > 0 ? (
          <div className="notice" data-easytag="id12-src/components/Home/index.jsx" style={{ marginTop: 8, color: '#8a6d3b' }}>
            Слишком много запросов. Повторите через {cooldown} сек.
          </div>
        ) : null}
        {importError ? (
          <div className="error" role="alert" aria-live="polite" data-easytag="id6-src/components/Home/index.jsx" style={{ marginTop: 8, color: '#d32f2f', fontSize: 12 }}>
            {importError}
          </div>
        ) : null}
      </div>

      <div className="card" data-easytag="id7-src/components/Home/index.jsx">
        <div className="actions" style={{ justifyContent: 'space-between', display: 'flex', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Популярные объявления</h2>
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

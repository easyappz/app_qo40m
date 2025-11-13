import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getAd, postView, rateAd, toggleFavorite } from '../../api/ads.jsx';
import { listByAd, create as createComment, toggleLike as toggleCommentLike, remove as removeComment } from '../../api/comments.jsx';
import { getMe } from '../../api/auth.jsx';

function formatPriceRub(minor) {
  if (typeof minor !== 'number' || Number.isNaN(minor)) return '—';
  const rub = minor / 100;
  try {
    return rub.toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
  } catch (_) {
    return `${Math.round(rub)} ₽`;
  }
}

export const Ad = () => {
  const { id } = useParams();
  const adId = Number(id);
  const navigate = useNavigate();

  const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;

  const [me, setMe] = useState(null);

  const [ad, setAd] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [favorite, setFavorite] = useState(null); // null: unknown, true/false known
  const [favLoading, setFavLoading] = useState(false);
  const [favError, setFavError] = useState('');

  const [ratingLoading, setRatingLoading] = useState(false);
  const [ratingError, setRatingError] = useState('');

  const [comments, setComments] = useState([]);
  const [commentsError, setCommentsError] = useState('');
  const [commentsLoading, setCommentsLoading] = useState(false);

  const [newComment, setNewComment] = useState('');
  const [createError, setCreateError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  const [replyForId, setReplyForId] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [replyLoading, setReplyLoading] = useState(false);
  const [replyError, setReplyError] = useState('');

  const [likedMap, setLikedMap] = useState({}); // commentId -> boolean

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError('');
    getAd(adId)
      .then((data) => {
        if (!mounted) return;
        setAd(data);
      })
      .catch((err) => setError(err.message || 'Не удалось загрузить объявление'))
      .finally(() => setLoading(false));

    // Post view (does not require auth)
    postView(adId).catch(() => {});

    // Load comments
    setCommentsLoading(true);
    listByAd(adId)
      .then((data) => setComments(Array.isArray(data.items) ? data.items : []))
      .catch((err) => setCommentsError(err.message || 'Не удалось загрузить комментарии'))
      .finally(() => setCommentsLoading(false));

    // Load me if authorized
    if (token) {
      getMe().then(setMe).catch(() => {});
    }

    return () => {
      mounted = false;
    };
  }, [adId, token]);

  const photos = useMemo(() => {
    if (!ad || !Array.isArray(ad.photos) || ad.photos.length === 0) {
      return [''];
    }
    return ad.photos;
  }, [ad]);

  const ensureAuth = () => {
    if (!token) {
      alert('Для этого действия необходимо войти.');
      navigate('/login');
      return false;
    }
    return true;
  };

  const onToggleFavorite = async () => {
    setFavError('');
    if (!ensureAuth()) return;
    setFavLoading(true);
    try {
      const res = await toggleFavorite(adId);
      setFavorite(Boolean(res.is_favorite));
    } catch (err) {
      setFavError(err.message || 'Не удалось изменить избранное');
    } finally {
      setFavLoading(false);
    }
  };

  const onRate = async (value) => {
    setRatingError('');
    if (!ensureAuth()) return;
    setRatingLoading(true);
    try {
      const updated = await rateAd(adId, value);
      setAd(updated);
    } catch (err) {
      setRatingError(err.message || 'Не удалось поставить оценку');
    } finally {
      setRatingLoading(false);
    }
  };

  const submitNewComment = async (e) => {
    e.preventDefault();
    setCreateError('');
    if (!ensureAuth()) return;
    const text = newComment.trim();
    if (!text) {
      setCreateError('Введите текст комментария.');
      return;
    }
    setCreateLoading(true);
    try {
      const created = await createComment(adId, { text });
      setComments((prev) => [created, ...prev]);
      setNewComment('');
    } catch (err) {
      setCreateError(err.message || 'Не удалось добавить комментарий');
    } finally {
      setCreateLoading(false);
    }
  };

  const submitReply = async (parentId) => {
    setReplyError('');
    if (!ensureAuth()) return;
    const text = replyText.trim();
    if (!text) {
      setReplyError('Введите текст ответа.');
      return;
    }
    setReplyLoading(true);
    try {
      const created = await createComment(adId, { text, parent: parentId });
      // Attach reply beneath the parent visually by incrementing counter and optionally showing inline
      setComments((prev) => prev.map((c) => (c.id === parentId ? { ...c, replies_count: (c.replies_count || 0) + 1 } : c)));
      setReplyText('');
      setReplyForId(null);
    } catch (err) {
      setReplyError(err.message || 'Не удалось добавить ответ');
    } finally {
      setReplyLoading(false);
    }
  };

  const toggleLike = async (commentId) => {
    if (!ensureAuth()) return;
    try {
      const res = await toggleCommentLike(commentId);
      setLikedMap((m) => ({ ...m, [commentId]: Boolean(res.is_liked) }));
      setComments((prev) => prev.map((c) => (c.id === commentId ? { ...c, likes_count: res.likes_count } : c)));
    } catch (_err) {
      // Non-blocking; optionally show toast
    }
  };

  const deleteComment = async (commentId) => {
    if (!ensureAuth()) return;
    if (!window.confirm('Удалить комментарий?')) return;
    try {
      await removeComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (err) {
      alert(err.message || 'Не удалось удалить комментарий');
    }
  };

  if (loading) {
    return (
      <section className="card" data-easytag="id1-src/components/Ad/index.jsx">
        <div className="muted">Загрузка…</div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="card" data-easytag="id1-src/components/Ad/index.jsx">
        <div className="error" role="alert">{error}</div>
        <div className="actions"><Link className="btn btn-secondary" to="/">На главную</Link></div>
      </section>
    );
  }

  if (!ad) return null;

  return (
    <section className="ad-page" data-easytag="id1-src/components/Ad/index.jsx">
      <div className="card" data-easytag="id2-src/components/Ad/index.jsx">
        <div className="ad-grid">
          <div className="ad-gallery" data-easytag="id3-src/components/Ad/index.jsx">
            {photos.map((src, i) => (
              <div key={i} className="ad-photo">
                {src ? <img src={src} alt="" /> : <div className="ad-photo-placeholder" />}
              </div>
            ))}
          </div>
          <div className="ad-info" data-easytag="id4-src/components/Ad/index.jsx">
            <h1 className="h1" style={{ marginBottom: 6 }}>{ad.title}</h1>
            <div className="muted" style={{ marginBottom: 12 }}>
              <a href={ad.source_url} target="_blank" rel="noreferrer" className="nav-link" data-easytag="id5-src/components/Ad/index.jsx">Открыть на Авито ↗</a>
            </div>
            <div className="ad-price" data-easytag="id6-src/components/Ad/index.jsx">{formatPriceRub(ad.price)}</div>
            <div className="ad-meta" data-easytag="id7-src/components/Ad/index.jsx">
              <span title="Рейтинг">★ {Number(ad.avg_rating || 0).toFixed(1)}</span>
              <span title="Просмотры">👁 {ad.views_count}</span>
              <span title="Комментарии">💬 {ad.comments_count}</span>
              <span title="Лайки">❤ {ad.likes_count}</span>
            </div>

            <div className="ad-actions" data-easytag="id8-src/components/Ad/index.jsx">
              <div className="rating" aria-label="Оценка" data-easytag="id9-src/components/Ad/index.jsx">
                {[1, 2, 3, 4, 5].map((v) => (
                  <button
                    key={v}
                    type="button"
                    className={`star ${ratingLoading ? 'disabled' : ''}`}
                    onClick={() => onRate(v)}
                    disabled={ratingLoading}
                    aria-label={`Поставить ${v}`}
                    data-easytag={`id10-${v}-src/components/Ad/index.jsx`}
                  >
                    {v}
                  </button>
                ))}
              </div>
              <button type="button" className="btn" onClick={onToggleFavorite} disabled={favLoading} data-easytag="id11-src/components/Ad/index.jsx">
                {favorite === true ? '★ В избранном' : '☆ В избранное'}
              </button>
            </div>
            {ratingError ? <div className="error" role="alert">{ratingError}</div> : null}
            {favError ? <div className="error" role="alert">{favError}</div> : null}

            <div className="ad-desc" data-easytag="id12-src/components/Ad/index.jsx">{ad.description}</div>
          </div>
        </div>
      </div>

      <div className="card" data-easytag="id13-src/components/Ad/index.jsx">
        <h2 style={{ margin: "0 0 8px" }}>Комментарии</h2>
        {token ? (
          <form className="form" onSubmit={submitNewComment} noValidate data-easytag="id14-src/components/Ad/index.jsx">
            <div className="form-row">
              <label htmlFor="new-comment">Добавить комментарий</label>
              <textarea
                id="new-comment"
                className="input"
                rows={3}
                placeholder="Поделитесь мнением…"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                data-easytag="id15-src/components/Ad/index.jsx"
              />
            </div>
            {createError ? <div className="error" role="alert">{createError}</div> : null}
            <div className="actions">
              <button type="submit" className="btn" disabled={createLoading} data-easytag="id16-src/components/Ad/index.jsx">{createLoading ? 'Отправка…' : 'Отправить'}</button>
            </div>
          </form>
        ) : (
          <div className="muted" data-easytag="id17-src/components/Ad/index.jsx">Чтобы писать комментарии, пожалуйста, <Link to="/login" className="nav-link">войдите</Link>.</div>
        )}

        {commentsLoading ? <div className="muted">Загрузка комментариев…</div> : null}
        {commentsError ? <div className="error" role="alert">{commentsError}</div> : null}

        <div className="comments" data-easytag="id18-src/components/Ad/index.jsx">
          {comments.map((c) => (
            <div key={c.id} className="comment" data-easytag="id19-src/components/Ad/index.jsx">
              <div className="comment-head">
                <div className="comment-author">
                  <div className="avatar" />
                  <div>
                    <div className="author-name">{c.author?.username || 'Пользователь'}</div>
                    <div className="muted small">{new Date(c.created_at).toLocaleString()}</div>
                  </div>
                </div>
                <div className="comment-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => toggleLike(c.id)} data-easytag="id20-src/components/Ad/index.jsx">❤ {c.likes_count}</button>
                  <button type="button" className="btn btn-secondary" onClick={() => setReplyForId(c.id)} data-easytag="id21-src/components/Ad/index.jsx">Ответить</button>
                  {me && c.author && me.id === c.author.id ? (
                    <button type="button" className="btn btn-secondary" onClick={() => deleteComment(c.id)} data-easytag="id22-src/components/Ad/index.jsx">Удалить</button>
                  ) : null}
                </div>
              </div>
              <div className="comment-text">{c.text}</div>
              {c.replies_count ? (
                <div className="muted small" style={{ marginTop: 6 }}>Ответов: {c.replies_count}</div>
              ) : null}

              {replyForId === c.id ? (
                <div className="reply" data-easytag="id23-src/components/Ad/index.jsx">
                  <textarea
                    className="input"
                    rows={2}
                    placeholder="Ваш ответ…"
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    data-easytag="id24-src/components/Ad/index.jsx"
                  />
                  {replyError ? <div className="error" role="alert">{replyError}</div> : null}
                  <div className="actions">
                    <button type="button" className="btn" onClick={() => submitReply(c.id)} disabled={replyLoading} data-easytag="id25-src/components/Ad/index.jsx">{replyLoading ? 'Отправка…' : 'Ответить'}</button>
                    <button type="button" className="btn btn-secondary" onClick={() => { setReplyForId(null); setReplyText(''); }} data-easytag="id26-src/components/Ad/index.jsx">Отмена</button>
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Ad;

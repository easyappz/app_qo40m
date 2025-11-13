import React from 'react';

export const Home = () => {
  return (
    <section className="home" data-easytag="id1-src/components/Home/index.jsx">
      <div className="hero">
        <h1 className="h1">Обсуждайте объявления с Авито</h1>
        <p className="muted">Вставьте ссылку на объявление, чтобы создать обсуждение.</p>
        <div className="hero-actions">
          <input
            type="text"
            className="input"
            placeholder="Вставьте ссылку на объявление с Авито"
            aria-label="Ссылка на объявление с Авито"
          />
          <button type="button" className="btn">Создать обсуждение</button>
        </div>
        <div className="muted small">Лента популярных объявлений появится ниже.</div>
      </div>
    </section>
  );
};

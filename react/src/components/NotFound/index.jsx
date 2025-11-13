import React from 'react';
import { Link } from 'react-router-dom';

const NotFound = () => {
  return (
    <section className="not-found" data-easytag="id1-src/components/NotFound/index.jsx">
      <h1 className="h1">404 — Страница не найдена</h1>
      <p className="muted">Похоже, такой страницы нет или она была перемещена.</p>
      <div className="actions">
        <Link to="/" className="btn">На главную</Link>
      </div>
    </section>
  );
};

export default NotFound;

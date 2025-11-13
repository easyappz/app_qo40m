import React from 'react';
import { useParams } from 'react-router-dom';

export const AdPage = () => {
  const { id } = useParams();
  return (
    <section className="card" data-easytag="id1-src/components/Ad/AdPage.jsx">
      <h1 className="h1">Объявление #{id}</h1>
      <p className="muted">Контент объявления будет здесь.</p>
    </section>
  );
};

import instance from './axios';

function extractErrorMessage(error) {
  const data = error?.response?.data;
  if (typeof data === 'string') return data;
  if (data?.detail) return data.detail;
  if (data?.message) return data.message;
  if (data && typeof data === 'object') {
    const firstKey = Object.keys(data)[0];
    const val = data[firstKey];
    if (Array.isArray(val) && val.length > 0) return String(val[0]);
    if (typeof val === 'string') return val;
  }
  return error?.message || 'Unknown error';
}

export async function importFromAvito(url) {
  try {
    const res = await instance.post('/api/ads/import/', { url });
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function getPopular({ limit, offset } = {}) {
  try {
    const res = await instance.get('/api/ads/popular/', { params: { limit, offset } });
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function getAd(id) {
  try {
    const res = await instance.get(`/api/ads/${id}/`);
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function postView(id) {
  try {
    const res = await instance.post(`/api/ads/${id}/views/`);
    return res.data; // { views_count }
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function rateAd(id, value) {
  try {
    const res = await instance.post(`/api/ads/${id}/ratings/`, { value });
    return res.data; // updated AdDetail
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function toggleFavorite(id) {
  try {
    const res = await instance.post(`/api/ads/${id}/favorite/`);
    return res.data; // { is_favorite }
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function getMyFavorites() {
  try {
    const res = await instance.get('/api/me/favorites/');
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function getMyAds() {
  try {
    const res = await instance.get('/api/me/ads/');
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

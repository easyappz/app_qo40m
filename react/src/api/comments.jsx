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

export async function listByAd(adId, { page } = {}) {
  try {
    const limit = 20;
    const p = typeof page === 'number' && page > 1 ? page : 1;
    const offset = (p - 1) * limit;
    const res = await instance.get(`/api/ads/${adId}/comments/`, { params: { limit, offset } });
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function create(adId, { text, parent } = {}) {
  try {
    const payload = { text };
    if (parent !== undefined && parent !== null) {
      payload.parent = parent;
    }
    const res = await instance.post(`/api/ads/${adId}/comments/`, payload);
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function remove(commentId) {
  try {
    await instance.delete(`/api/comments/${commentId}/`);
    return { ok: true };
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function toggleLike(commentId) {
  try {
    const res = await instance.post(`/api/comments/${commentId}/like/`);
    return res.data; // { is_liked, likes_count }
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

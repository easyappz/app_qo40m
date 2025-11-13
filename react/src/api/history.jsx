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

export async function getMyHistory() {
  try {
    const res = await instance.get('/api/me/history/');
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

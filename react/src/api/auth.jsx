import instance from './axios';

function extractErrorMessage(error) {
  const data = error?.response?.data;
  if (typeof data === 'string') return data;
  if (data?.detail) return data.detail;
  if (data?.message) return data.message;
  if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length > 0) return data.non_field_errors[0];
  if (data && typeof data === 'object') {
    const firstKey = Object.keys(data)[0];
    const val = data[firstKey];
    if (Array.isArray(val) && val.length > 0) return String(val[0]);
    if (typeof val === 'string') return val;
  }
  return error?.message || 'Unknown error';
}

export async function register(data) {
  try {
    const res = await instance.post('/api/auth/register/', data);
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function login(data) {
  try {
    const res = await instance.post('/api/auth/login/', data);
    return res.data; // { access, refresh }
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function refresh(refreshToken) {
  try {
    const res = await instance.post('/api/auth/refresh/', { refresh: refreshToken });
    return res.data; // { access, refresh }
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function getMe() {
  try {
    const res = await instance.get('/api/me/');
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function updateMe(data) {
  try {
    const res = await instance.patch('/api/me/', data);
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

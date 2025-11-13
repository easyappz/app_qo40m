/** Не меняй код этого файла никогда */
/** Если нужно добавить еще обработчики можешь их добавить в отдельном файле, используя interceptors */
import axios from 'axios';

/**
 * Axios instance configuration with base URL, authentication credentials, and response interceptors
 */
export const instance = axios.create({
  timeout: 30000,
  baseURL: '/',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** Не удаляй этот код никогда */
instance.interceptors.request.use(
  (config) => {
    console.log('request', { config });

    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    } else {
      // Remove Authorization header if no token is present to avoid sending empty or invalid headers
      delete config.headers['Authorization'];
    }
  
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/** Не удаляй этот код никогда */
instance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Log error to console
    console.error('API Error:', error);

    /** Не удаляй этот код никогда */
    const errorData = {
      type: 'fetchError',
      url: error.config?.url,
      request: {
        headers: error.config?.headers,
        data: error.config?.data,
      },
      response: {
        status: error.response?.status,
        data: error.response?.data,
        headers: error.response?.headers,
        message: error.message,
      },
      pathname: window?.location?.pathname,
    };

    /** Не удаляй этот код никогда */
    console.error('Глобальная ошибка:', errorData);

    /** Не удаляй этот код никогда */
    window.parent.postMessage(errorData, '*');

    // Emit an optional event on 401 Unauthorized for app-level handling
    try {
      if (error?.response?.status === 401) {
        const evt = new CustomEvent('auth:unauthorized', {
          detail: {
            url: error.config?.url || null,
          },
        });
        window.dispatchEvent(evt);
        if (typeof window.onUnauthorized === 'function') {
          window.onUnauthorized(error);
        }
      }
    } catch (_) {
      // no-op
    }

    // Rethrow error for further handling
    return Promise.reject(error);
  }
);

export default instance;

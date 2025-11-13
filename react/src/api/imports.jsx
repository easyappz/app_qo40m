import instance from './axios';

export const createImport = (url) => instance.post('/api/imports/', { url });

export const getImportStatus = (id) => instance.get(`/api/imports/${id}/`);

export default { createImport, getImportStatus };
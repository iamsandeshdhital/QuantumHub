import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:3000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth tokens
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token might be expired - clear auth state
      localStorage.removeItem('token');
    }
    return Promise.reject(error);
  }
);

export const papersApi = {
  getAll: (params = {}) => api.get('/papers', { params }),
  getById: (id) => api.get(`/papers/${id}`),
  getByInstitution: (institution) => api.get(`/papers/institution/${institution}`),
  getByTag: (tag) => api.get(`/papers/tag/${tag}`),
  search: (query) => api.get(`/api/search?query=${encodeURIComponent(query)}`),
};

export const projectsApi = {
  getAll: (params = {}) => api.get('/api/projects', { params }),
  getById: (id) => api.get(`/api/projects/${id}`),
};

export const analyticsApi = {
  getAnalytics: () => api.get('/api/analytics'),
};

export default api;
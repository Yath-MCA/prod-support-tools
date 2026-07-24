import api from './axiosInstance'

export const authApi = {
  /** Preferred: POST /auth/login */
  login: (token) => api.post('/auth/login', { token }),
  /** Alias kept for existing callers */
  loginToken: (token) => api.post('/auth/token', { token }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

export const configApi = {
  impact: () => api.get('/config/impact'),
  /** Mantis /config with impact.json fallback */
  config: (option) =>
    api.get('/config', { params: option ? { option } : {} }),
  health: () => api.get('/health'),
}

export const ticketsApi = {
  list: (params) => api.get('/tickets', { params }),
  get: (id) => api.get(`/tickets/${id}`),
  create: (body) => api.post('/tickets', body),
  update: (id, body) => api.patch(`/tickets/${id}`, body),
  addNote: (id, body) => api.post(`/tickets/${id}/notes`, body),
  deleteNote: (id, noteId) => api.delete(`/tickets/${id}/notes/${noteId}`),
  closeOrDelete: (id, mode = 'close') =>
    api.delete(`/tickets/${id}`, { params: { mode } }),
}

export const lookupApi = {
  projects: () => api.get('/projects'),
  project: (id) => api.get(`/projects/${id}`),
  users: (projectId) =>
    api.get('/users', { params: projectId ? { project_id: projectId } : {} }),
  handlers: (projectId) =>
    api.get('/handlers', { params: { project_id: projectId } }),
  filters: (params) => api.get('/filters', { params }),
  filter: (id) => api.get(`/filters/${id}`),
}

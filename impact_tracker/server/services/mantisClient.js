const axios = require('axios')



const BASE = (process.env.MANTIS_BASE_URL || 'https://mantis.newgen.co').replace(/\/$/, '')



/**

 * Map a Mantis REST response into an Error with { status, message, mantis }.

 */

function mapMantisError(res, fallback) {

  const msg =

    res.data?.message ||

    res.data?.localized ||

    (typeof res.data === 'string' ? res.data : null) ||

    fallback ||

    `Mantis error ${res.status}`

  const err = new Error(msg)

  err.status = res.status

  err.mantis = res.data

  return err

}



/**

 * Per-request Mantis REST client bound to an API token.

 * @param {string} token

 */

function createMantisClient(token) {

  if (!token || typeof token !== 'string') {

    throw new Error('Mantis API token is required')

  }



  const http = axios.create({

    baseURL: `${BASE}/api/rest`,

    timeout: 30_000,

    headers: {

      Accept: 'application/json',

      'Content-Type': 'application/json',

      Authorization: token.trim(),

    },

    validateStatus: () => true,

  })



  async function getMe() {

    const res = await http.get('/users/me')

    if (res.status >= 400) throw mapMantisError(res, 'Invalid API token')

    return res.data

  }



  async function listIssues(query = {}) {

    const res = await http.get('/issues', { params: query })

    if (res.status >= 400) throw mapMantisError(res, 'Failed to list issues')

    return res.data

  }



  async function getIssue(id) {

    const res = await http.get(`/issues/${id}`)

    if (res.status >= 400) throw mapMantisError(res, `Failed to get issue ${id}`)

    return res.data

  }



  async function createIssue(body) {

    const res = await http.post('/issues', body)

    if (res.status >= 400) throw mapMantisError(res, 'Failed to create issue')

    return res.data

  }



  async function updateIssue(id, body) {

    const res = await http.patch(`/issues/${id}`, body)

    if (res.status >= 400) throw mapMantisError(res, `Failed to update issue ${id}`)

    return res.data

  }



  async function deleteIssue(id) {

    const res = await http.delete(`/issues/${id}`)

    if (res.status >= 400) throw mapMantisError(res, `Failed to delete issue ${id}`)

    return res.data

  }



  async function addNote(id, body) {

    const res = await http.post(`/issues/${id}/notes`, body)

    if (res.status >= 400) throw mapMantisError(res, 'Failed to add note')

    return res.data

  }



  async function deleteNote(issueId, noteId) {

    const res = await http.delete(`/issues/${issueId}/notes/${noteId}`)

    if (res.status >= 400) throw mapMantisError(res, 'Failed to delete note')

    return res.data

  }



  async function listProjects() {

    const res = await http.get('/projects')

    if (res.status >= 400) throw mapMantisError(res, 'Failed to list projects')

    return res.data

  }



  async function getProject(id) {

    const res = await http.get(`/projects/${id}`)

    if (res.status >= 400) throw mapMantisError(res, `Failed to get project ${id}`)

    return res.data

  }



  async function listUsers(projectId) {

    const path = projectId ? `/projects/${projectId}/users` : '/users/me'

    const res = await http.get(path)

    if (res.status >= 400) {

      if (projectId) return { users: [] }

      throw mapMantisError(res, 'Failed to list users')

    }

    return res.data

  }



  async function listHandlers(projectId) {

    if (!projectId) {

      const err = new Error('project_id is required for handlers')

      err.status = 400

      throw err

    }

    const res = await http.get(`/projects/${projectId}/handlers`)

    if (res.status >= 400) {

      // Soft-fail — some installs lack handlers endpoint

      return { handlers: [] }

    }

    return res.data

  }



  async function listFilters(query = {}) {

    const res = await http.get('/filters', { params: query })

    if (res.status >= 400) throw mapMantisError(res, 'Failed to list filters')

    return res.data

  }



  async function getFilter(id) {

    const res = await http.get(`/filters/${id}`)

    if (res.status >= 400) throw mapMantisError(res, `Failed to get filter ${id}`)

    return res.data

  }



  async function getConfig(option = undefined) {

    const params = option ? { option } : undefined

    const res = await http.get('/config', { params })

    if (res.status >= 400) throw mapMantisError(res, 'Failed to get config')

    return res.data

  }



  return {

    http,

    getMe,

    listIssues,

    getIssue,

    createIssue,

    updateIssue,

    deleteIssue,

    addNote,

    deleteNote,

    listProjects,

    getProject,

    listUsers,

    listHandlers,

    listFilters,

    getFilter,

    getConfig,

  }

}



module.exports = {

  BASE,

  createMantisClient,

  mapMantisError,

}


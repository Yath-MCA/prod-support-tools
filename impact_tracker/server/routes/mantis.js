const express = require('express')

const fs = require('fs')

const path = require('path')

const {

  requireAuth,

  shapeUser,

  setSession,

  clearSession,

  getSessionUser,

  hasSession,

  resolveToken,

} = require('../auth/sessionAuth')

const { createMantisClient, BASE } = require('../services/mantisClient')



const router = express.Router()



function clientFor(req) {

  return createMantisClient(req.mantisToken)

}



function sendMantisError(res, err) {

  const status = err.status && err.status >= 400 ? err.status : 502

  return res.status(status).json({

    message: err.message || 'Mantis request failed',

    status,

    mantis: err.mantis ?? null,

  })

}



function loadImpactConfig() {

  const configPath = path.join(__dirname, '../../config/impact.json')

  const raw = fs.readFileSync(configPath, 'utf8')

  return JSON.parse(raw)

}



// ——— Auth ———



async function loginHandler(req, res) {

  try {

    const token = req.body?.token

    if (!token || typeof token !== 'string') {

      return res.status(400).json({ message: 'token is required' })

    }



    const trimmed = token.trim()

    const me = await createMantisClient(trimmed).getMe()

    const user = shapeUser(me)

    setSession(req, { token: trimmed, user })



    return res.json({ ok: true, user })

  } catch (err) {

    clearSession(req)

    return sendMantisError(res, err)

  }

}



/** Preferred login route */

router.post('/auth/login', loginHandler)

/** Alias for existing UI */

router.post('/auth/token', loginHandler)



router.post('/auth/logout', (req, res) => {

  clearSession(req)

  return res.json({ ok: true })

})



router.get('/auth/me', (req, res) => {

  // Session user preferred; Authorization-only callers get a live /users/me

  if (hasSession(req)) {

    return res.json({ user: getSessionUser(req), authMode: 'token' })

  }



  const token = resolveToken(req)

  if (!token) {

    return res.status(401).json({ message: 'Not authenticated' })

  }



  createMantisClient(token)

    .getMe()

    .then((me) => res.json({ user: shapeUser(me), authMode: 'token' }))

    .catch((err) => sendMantisError(res, err))

})



// ——— Health / Config ———



router.get('/health', (req, res) => {

  res.json({

    status: 'ok',

    mantisBase: BASE,

    authenticated: Boolean(resolveToken(req)),

    authMode: 'token',

  })

})



/** Local Impact presets (always available, no Mantis auth) */

router.get('/config/impact', (_req, res) => {

  try {

    return res.json(loadImpactConfig())

  } catch (err) {

    return res.status(500).json({ message: 'Failed to read impact config', detail: err.message })

  }

})



/**

 * Mantis GET /config — enums/options from upstream.

 * Falls back to local impact.json when Mantis is unreachable or unauthenticated.

 */

router.get('/config', async (req, res) => {

  const token = resolveToken(req)

  if (token) {

    try {

      const data = await createMantisClient(token).getConfig(req.query.option)

      return res.json(data)

    } catch (err) {

      // fall through to local config

      console.warn('Mantis /config failed, falling back to impact.json:', err.message)

    }

  }



  try {

    const impact = loadImpactConfig()

    return res.json({ source: 'impact.json', config: impact })

  } catch (err) {

    return res.status(500).json({ message: 'Failed to read config', detail: err.message })

  }

})



// ——— Tickets (UI aliases for /issues) ———



router.get('/tickets', requireAuth, async (req, res) => {

  try {

    const {

      project_id,

      filter_id,

      page = 1,

      page_size = 50,

      select,

    } = req.query



    const params = {

      page: Number(page) || 1,

      page_size: Math.min(Number(page_size) || 50, 100),

    }

    if (project_id) params.project_id = project_id

    if (filter_id) params.filter_id = filter_id

    if (select) params.select = select



    const data = await clientFor(req).listIssues(params)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.get('/tickets/:id', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).getIssue(req.params.id)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.post('/tickets', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).createIssue(req.body)

    return res.status(201).json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.patch('/tickets/:id', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).updateIssue(req.params.id, req.body)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.post('/tickets/:id/notes', requireAuth, async (req, res) => {

  try {

    const text = req.body?.text ?? req.body?.note?.text

    if (!text) return res.status(400).json({ message: 'note text is required' })



    const body = {

      text,

      view_state: req.body.view_state || { name: 'public' },

    }

    const data = await clientFor(req).addNote(req.params.id, body)

    return res.status(201).json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.delete('/tickets/:id/notes/:noteId', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).deleteNote(req.params.id, req.params.noteId)

    return res.json(data || { ok: true })

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.delete('/tickets/:id', requireAuth, async (req, res) => {

  try {

    // Prefer close when ?mode=close (default); hard delete with ?mode=delete

    const mode = (req.query.mode || 'close').toLowerCase()

    if (mode === 'delete') {

      const data = await clientFor(req).deleteIssue(req.params.id)

      return res.json(data || { ok: true })

    }

    const data = await clientFor(req).updateIssue(req.params.id, {

      status: { name: 'closed' },

    })

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



// ——— Projects ———



router.get('/projects', requireAuth, async (_req, res) => {

  try {

    const data = await clientFor(_req).listProjects()

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.get('/projects/:id', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).getProject(req.params.id)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.get('/projects/:id/handlers', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).listHandlers(req.params.id)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



// ——— Users / handlers ———



router.get('/users', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).listUsers(req.query.project_id)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



/** Convenience: handlers for a project via query (?project_id=) */

router.get('/handlers', requireAuth, async (req, res) => {

  try {

    const projectId = req.query.project_id

    if (!projectId) {

      return res.status(400).json({ message: 'project_id is required' })

    }

    const data = await clientFor(req).listHandlers(projectId)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



// ——— Filters ———



router.get('/filters', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).listFilters(req.query)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



router.get('/filters/:id', requireAuth, async (req, res) => {

  try {

    const data = await clientFor(req).getFilter(req.params.id)

    return res.json(data)

  } catch (err) {

    return sendMantisError(res, err)

  }

})



module.exports = router


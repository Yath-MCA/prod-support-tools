/**

 * Per-request session / Authorization helpers for the Mantis Bridge.

 *

 * Token resolution order:

 *   1. Authorization header (passthrough — does not mutate session)

 *   2. Cookie session (req.session.mantisToken)

 */



function normalizeToken(raw) {

  if (!raw || typeof raw !== 'string') return null

  const trimmed = raw.trim()

  if (!trimmed) return null

  // Accept "Bearer <token>" or raw Mantis API token

  return trimmed.replace(/^Bearer\s+/i, '').trim() || null

}



/**

 * Resolve the Mantis API token for this request.

 * @param {import('express').Request} req

 * @returns {string|null}

 */

function resolveToken(req) {

  const headerToken = normalizeToken(req.headers.authorization)

  if (headerToken) return headerToken

  return normalizeToken(req.session?.mantisToken)

}



/**

 * Express middleware — requires a session or Authorization token.

 * Sets req.mantisToken for downstream handlers.

 */

function requireAuth(req, res, next) {

  const token = resolveToken(req)

  if (!token) {

    return res.status(401).json({

      message: 'Not authenticated. Paste a Mantis API token first.',

    })

  }

  req.mantisToken = token

  return next()

}



/**

 * Shape a Mantis /users/me payload into a stable bridge user object.

 */

function shapeUser(me) {

  const user = me?.user || me || { name: 'mantis-user' }

  return {

    id: user.id,

    name: user.name || user.real_name || user.username,

    email: user.email,

    access_level: user.access_level,

  }

}



/**

 * Store token + user on the cookie session.

 */

function setSession(req, { token, user }) {

  if (!req.session) {

    throw new Error('Session middleware is not configured')

  }

  req.session.mantisToken = token

  req.session.user = user

}



/**

 * Clear the cookie session.

 */

function clearSession(req) {

  if (!req.session) return

  req.session = null

}



/**

 * @param {import('express').Request} req

 */

function getSessionUser(req) {

  return req.session?.user || null

}



/**

 * @param {import('express').Request} req

 */

function hasSession(req) {

  return Boolean(normalizeToken(req.session?.mantisToken))

}



module.exports = {

  resolveToken,

  requireAuth,

  shapeUser,

  setSession,

  clearSession,

  getSessionUser,

  hasSession,

  normalizeToken,

}


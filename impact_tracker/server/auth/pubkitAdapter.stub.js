/**
 * PubKit SSO Auth Adapter — STUB (not implemented)
 * -------------------------------------------------
 * Team decision pending. When PubKit SSO is confirmed
 * (https://pubkit.newgen.co/ → mantis.newgen.co), implement this
 * class with the same AuthAdapter surface as TokenAuthAdapter:
 *
 *   isAuthenticated()
 *   getAuthHeaders()
 *   login(credentials)
 *   logout()
 *   getUser()
 *
 * Likely approach (TBD with team):
 *   - Redirect browser to PubKit login
 *   - Receive session cookie / token
 *   - Forward Cookie or derived Mantis credentials on REST calls
 *
 * Swap in server/index.js by selecting adapter from env AUTH_MODE=pubkit|token
 * Frontend keeps AuthContext + ticket screens unchanged.
 */

class PubKitAuthAdapter {
  constructor() {
    throw new Error(
      'PubKitAuthAdapter is not implemented yet. Use TokenAuthAdapter until the team confirms SSO.'
    )
  }
}

module.exports = { PubKitAuthAdapter }

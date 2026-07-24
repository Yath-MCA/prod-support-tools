/**

 * AuthAdapter seam (pluggable)

 * -----------------------------

 * MVP auth is per-user cookie session — see sessionAuth.js.

 * This module keeps a thin TokenAuthAdapter class for the AuthAdapter

 * interface docs / future PubKit swap; the Express bridge no longer

 * uses a process-wide token singleton.

 *

 * Prefer: require('./sessionAuth') for request-scoped token resolution.

 */



class TokenAuthAdapter {

  constructor() {

    this._token = null

    this._user = null

  }



  isAuthenticated() {

    return Boolean(this._token)

  }



  getAuthHeaders() {

    if (!this._token) return {}

    return { Authorization: this._token }

  }



  getToken() {

    return this._token

  }



  getUser() {

    return this._user

  }



  /**

   * @param {{ token: string, user?: object }} credentials

   */

  login({ token, user = null }) {

    if (!token || typeof token !== 'string') {

      throw new Error('API token is required')

    }

    this._token = token.trim()

    this._user = user

    return { ok: true, user: this._user }

  }



  logout() {

    this._token = null

    this._user = null

  }

}



module.exports = {

  TokenAuthAdapter,

}


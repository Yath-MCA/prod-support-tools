require('dotenv').config({ path: require('path').join(__dirname, '../.env.local') })

require('dotenv').config({ path: require('path').join(__dirname, '../.env') })



const express = require('express')

const cors = require('cors')

const helmet = require('helmet')

const cookieSession = require('cookie-session')

const { resolveToken } = require('./auth/sessionAuth')

const mantisRoutes = require('./routes/mantis')



const app = express()

const PORT = Number(process.env.PROXY_PORT) || 5100

const AUTH_MODE = (process.env.AUTH_MODE || 'token').toLowerCase()

const SESSION_SECRET = process.env.SESSION_SECRET || 'impact-tracker-dev-secret-change-me'



// Auth adapter seam: MVP uses token session. Set AUTH_MODE=pubkit when PubKit SSO is implemented.

if (AUTH_MODE === 'pubkit') {

  console.warn(

    'AUTH_MODE=pubkit requested but PubKitAuthAdapter is stubbed — falling back to token session.'

  )

}



app.use(helmet({ contentSecurityPolicy: false }))

app.use(

  cors({

    origin: true,

    credentials: true,

  })

)

app.use(express.json({ limit: '2mb' }))

app.use(

  cookieSession({

    name: 'impact_session',

    keys: [SESSION_SECRET],

    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days

    httpOnly: true,

    sameSite: 'lax',

    secure: process.env.NODE_ENV === 'production',

  })

)



app.get('/health', (req, res) => {

  res.json({

    status: 'ok',

    authenticated: Boolean(resolveToken(req)),

    authMode: AUTH_MODE === 'pubkit' ? 'token-fallback' : 'token',

  })

})



app.use('/api', mantisRoutes)



app.use((err, _req, res, _next) => {

  console.error(err)

  res.status(500).json({ message: err.message || 'Internal server error' })

})



app.listen(PORT, () => {

  console.log(`Impact Tracker Bridge → http://localhost:${PORT}`)

  console.log(`Mantis base → ${process.env.MANTIS_BASE_URL || 'https://mantis.newgen.co'}`)

  console.log(`Auth mode → per-user cookie session (PubKit adapter stubbed for later)`)

})


require('dotenv').config({ path: require('path').join(__dirname, '../.env.local') })
const express     = require('express')
const mongoose    = require('mongoose')
const cors        = require('cors')
const helmet      = require('helmet')
const compression = require('compression')

const app  = express()
const PORT = process.env.PORT || 5000
const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/XMLEDITOR'

app.use(helmet())
app.use(compression())
app.use(cors())
app.use(express.json())

// Health check
app.get('/health', (_req, res) => res.json({ status: 'ok', db: mongoose.connection.readyState }))

// List all user databases on this connection (excludes admin / local / config)
app.get('/databases', async (_req, res) => {
  try {
    const { databases } = await mongoose.connection.db.admin().listDatabases()
    const result = databases
      .filter((d) => !['admin', 'local', 'config'].includes(d.name))
      .map((d) => ({ name: d.name, sizeOnDisk: d.sizeOnDisk }))
    res.json(result)
  } catch (err) {
    res.status(500).json({ message: err.message })
  }
})

// API routes
app.use('/api', require('./routes/api'))

// Connect to MongoDB then start server
mongoose
  .connect(MONGO_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true
  })
  .then(() => {
    console.log(`MongoDB connected → ${MONGO_URI}`)
    app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`))
  })
  .catch((err) => {
    console.error('MongoDB connection failed:', err.message)
    process.exit(1)
  })

mongoose.connection.on('disconnected', () => console.warn('MongoDB disconnected'))
mongoose.connection.on('reconnected',  () => console.log('MongoDB reconnected'))

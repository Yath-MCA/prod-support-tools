const mongoose = require('mongoose')

// Schemas defined here so they can be reused across any database connection
const rFilesListSchema = new mongoose.Schema(
  { docid: String, identifier: String, timeiso_c: Date, username: String,
    timestamp: String, recordtype: String, rolename: String },
  { strict: false }
)

const rDocViewHistorySchema = new mongoose.Schema(
  { docid: String, identifier: String, timeiso_c: Date, username: String,
    session_id: String, rolename: String },
  { strict: false }
)

const rLinkSharingSchema = new mongoose.Schema(
  { docid: String, identifier: String, timeiso_c: Date, username: String,
    session_id: String, process: String, remarks: String,
    session_end_time: Date, rolename: String },
  { strict: false }
)

/**
 * Returns Mongoose models bound to the requested database.
 * useDb with useCache:true re-uses the same underlying connection
 * per dbName — no new TCP connections are created.
 */
function getModels(dbName) {
  const conn = mongoose.connection.useDb(dbName, { useCache: true })
  return {
    RFilesList:      conn.models.RFilesList      || conn.model('RFilesList',      rFilesListSchema,      'rFileslist'),
    RDocViewHistory: conn.models.RDocViewHistory || conn.model('RDocViewHistory', rDocViewHistorySchema, 'rdocviewhistory'),
    RLinkSharing:    conn.models.RLinkSharing    || conn.model('RLinkSharing',    rLinkSharingSchema,    'rlinksharing'),
  }
}

module.exports = getModels

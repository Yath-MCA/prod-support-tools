const mongoose = require('mongoose')

const schema = new mongoose.Schema(
  {
    docid:            { type: String },    // primary key — preferred
    identifier:       { type: String },    // fallback / alias
    timeiso_c:        { type: Date },
    username:         { type: String },
    session_id:       { type: String },
    process:          { type: String },
    remarks:          { type: String },
    session_end_time: { type: Date },
    rolename:         { type: String },    // optional
  },
  { strict: false }
)

module.exports = mongoose.model('RLinkSharing', schema, 'rlinksharing')

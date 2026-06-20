const mongoose = require('mongoose')

const schema = new mongoose.Schema(
  {
    docid:      { type: String },          // primary key — preferred
    identifier: { type: String },          // fallback / alias
    timeiso_c:  { type: Date },
    username:   { type: String },
    session_id: { type: String },
    rolename:   { type: String },          // optional
  },
  { strict: false }
)

module.exports = mongoose.model('RDocViewHistory', schema, 'rdocviewhistory')

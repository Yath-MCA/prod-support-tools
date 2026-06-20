const router    = require('express').Router()
const axios     = require('axios')
const getModels = require('../models/getModels')
const escapeStringRegexp = require('escape-string-regexp')

const DEFAULT_DB = 'XMLEDITOR'

function db(req) {
  return req.query.db || DEFAULT_DB
}

function dateFilter(query) {
  const filter = {}
  if (query.dateFrom || query.dateTo) {
    filter.timeiso_c = {}
    if (query.dateFrom) filter.timeiso_c.$gte = new Date(query.dateFrom)
    if (query.dateTo)   filter.timeiso_c.$lte = new Date(query.dateTo + 'T23:59:59.999Z')
  }
  return filter
}

function docKeyFilter(query) {
  if (!query.docid && !query.identifier) return {}
  const val = query.docid || query.identifier
  return { $or: [{ docid: val }, { identifier: val }] }
}

function pagination(query) {
  const page  = Math.max(1, parseInt(query.page)  || 1)
  const limit = Math.min(500, Math.max(1, parseInt(query.limit) || 100))
  return { skip: (page - 1) * limit, limit }
}

// GET /api/rFileslist
router.get('/rFileslist', async (req, res) => {
  try {
    const { RFilesList } = getModels(db(req))
    const filter = { ...dateFilter(req.query), ...docKeyFilter(req.query) }
    if (req.query.username)   filter.username   = req.query.username
    if (req.query.recordtype) filter.recordtype = req.query.recordtype
    if (req.query.rolename)   filter.rolename   = req.query.rolename

    const { skip, limit } = pagination(req.query)
    const [data, total] = await Promise.all([
      RFilesList.find(filter).sort({ timeiso_c: -1 }).skip(skip).limit(limit).lean(),
      RFilesList.countDocuments(filter),
    ])
    res.json({ data, total, page: req.query.page || 1, limit })
  } catch (err) {
    res.status(500).json({ message: err.message })
  }
})

// GET /api/rdocviewhistory
router.get('/rdocviewhistory', async (req, res) => {
  try {
    const { RDocViewHistory } = getModels(db(req))
    const filter = { ...dateFilter(req.query), ...docKeyFilter(req.query) }
    if (req.query.username)   filter.username   = req.query.username
    if (req.query.session_id) filter.session_id = req.query.session_id
    if (req.query.rolename)   filter.rolename   = req.query.rolename

    const { skip, limit } = pagination(req.query)
    const [data, total] = await Promise.all([
      RDocViewHistory.find(filter).sort({ timeiso_c: -1 }).skip(skip).limit(limit).lean(),
      RDocViewHistory.countDocuments(filter),
    ])
    res.json({ data, total, page: req.query.page || 1, limit })
  } catch (err) {
    res.status(500).json({ message: err.message })
  }
})

// GET /api/rlinksharing
router.get('/rlinksharing', async (req, res) => {
  try {
    const { RLinkSharing } = getModels(db(req))
    const filter = { ...dateFilter(req.query), ...docKeyFilter(req.query) }
    if (req.query.username)   filter.username   = req.query.username
    if (req.query.session_id) filter.session_id = req.query.session_id
    if (req.query.process)    filter.process    = req.query.process
    if (req.query.rolename)   filter.rolename   = req.query.rolename

    const { skip, limit } = pagination(req.query)
    const [data, total] = await Promise.all([
      RLinkSharing.find(filter).sort({ timeiso_c: -1 }).skip(skip).limit(limit).lean(),
      RLinkSharing.countDocuments(filter),
    ])
    res.json({ data, total, page: req.query.page || 1, limit })
  } catch (err) {
    res.status(500).json({ message: err.message })
  }
})

// GET /api/activity  — three collections merged, sorted by timeiso_c desc
router.get('/activity', async (req, res) => {
  try {
    console.log('[API] /activity endpoint hit', req.query);
    // Build identifier regex
    const identifier = req.query.identifier || req.query.docid || '';
    const identifierRegex = identifier ? { "$regex": escapeStringRegexp(identifier), "$options": "i" } : undefined;

    // Build recordtype regex for Fileslist and UserPreference
    const filesRecordType = { "$regex": "save|autosave", "$options": "i" };
    const userPrefRecordType = { "$regex": "open_close_dialog|query_quick_answer|guided_tour_image|guided_tour|pdf_download|fetch_doi|fetch_plainText|insert_symbol|find_list|replace_list|video_tour|support_mail", "$options": "i" };

    // Prepare POST bodies
    const postBodies = [
      {
        tbl: "Fileslist",
        length: 500,
        find: Object.assign(
          {},
          identifierRegex ? { identifier: identifierRegex } : {},
          { recordtype: filesRecordType }
        ),
        filter: []
      },
      {
        tbl: "docviewhistory",
        length: 500,
        find: identifierRegex ? { identifier: identifierRegex } : {},
        filter: []
      },
      {
        tbl: "linksharing",
        length: 500,
        find: identifierRegex ? { identifier: identifierRegex } : {},
        filter: []
      },
      {
        tbl: "UserPreference",
        length: 500,
        find: Object.assign(
          {},
          identifierRegex ? { identifier: identifierRegex } : {},
          { recordtype: userPrefRecordType }
        ),
        filter: []
      }
    ];

    // Java backend endpoint
    const javaEndpoint = process.env.JAVA_API_ENDPOINT || "http://localhost:8080/impactapinew/getdocs";

    // Fire all requests in parallel
    const [filesRes, historyRes, linksRes, userPrefRes] = await Promise.all(postBodies.map(body =>
      axios.post(javaEndpoint, body).then(r => r.data && Array.isArray(r.data) ? r.data : []).catch(() => [])
    ));

    // Tag results
    const tagged = [
      ...filesRes.map((r)      => ({ ...r, _source: 'rFileslist' })),
      ...historyRes.map((r)   => ({ ...r, _source: 'rdocviewhistory' })),
      ...linksRes.map((r)     => ({ ...r, _source: 'rlinksharing' })),
      ...userPrefRes.map((r)  => ({ ...r, _source: 'userpreference' })),
    ];

    // Sort by timeiso_c desc
    tagged.sort((a, b) => {
      const ta = a.timeiso_c ? new Date(a.timeiso_c).getTime() : 0;
      const tb = b.timeiso_c ? new Date(b.timeiso_c).getTime() : 0;
      return tb - ta;
    });

    const total = tagged.length;
    const page  = Math.max(1, parseInt(req.query.page) || 1);
    const limit = Math.min(500, Math.max(1, parseInt(req.query.limit) || 100));
    const data  = tagged.slice((page - 1) * limit, page * limit);

    res.json({ data, total, page, limit });
  } catch (err) {
    res.status(500).json({ message: err.message })
  }
})

module.exports = router

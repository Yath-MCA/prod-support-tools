const roles = ['Admin', 'Editor', 'Viewer', 'Manager', 'Auditor']
const recordTypes = ['PDF', 'DOCX', 'XLSX', 'Image', 'Video']
const users = ['alice', 'bob', 'carol', 'dave', 'eve', 'frank', 'grace']
const processes = ['download', 'preview', 'share', 'print', 'export']

function rnd(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

function genId(prefix) {
  return `${prefix}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`
}

function genDate(daysBack = 30) {
  const d = new Date()
  d.setDate(d.getDate() - Math.floor(Math.random() * daysBack))
  d.setHours(Math.floor(Math.random() * 24), Math.floor(Math.random() * 60))
  return d.toISOString()
}

// ~half the mock records use docid, half use identifier — mirrors real-world variance
function genDocKey() {
  return Math.random() > 0.5
    ? { docid: genId('DOC') }
    : { identifier: genId('DOC') }
}

export function genRFilesList(n = 80) {
  return Array.from({ length: n }, () => ({
    _id: genId('F'),
    ...genDocKey(),
    timeiso_c:  genDate(60),
    username:   rnd(users),
    timestamp:  genDate(60),
    recordtype: rnd(recordTypes),
    rolename:   Math.random() > 0.3 ? rnd(roles) : undefined,  // optional
  }))
}

export function genRDocViewHistory(n = 60) {
  return Array.from({ length: n }, () => ({
    _id:        genId('H'),
    ...genDocKey(),
    timeiso_c:  genDate(30),
    username:   rnd(users),
    session_id: genId('SES'),
    rolename:   Math.random() > 0.3 ? rnd(roles) : undefined,  // optional
  }))
}

export function genRLinkSharing(n = 50) {
  return Array.from({ length: n }, () => ({
    _id:              genId('L'),
    ...genDocKey(),
    timeiso_c:        genDate(30),
    username:         rnd(users),
    session_id:       genId('SES'),
    process:          rnd(processes),
    remarks:          Math.random() > 0.5 ? 'Shared externally' : '',
    session_end_time: genDate(30),
    rolename:         Math.random() > 0.3 ? rnd(roles) : undefined,  // optional
  }))
}

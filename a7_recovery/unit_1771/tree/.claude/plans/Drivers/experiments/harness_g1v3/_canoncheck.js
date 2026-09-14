// zero-LLM pre-flight: does the workflow's JS h32(canon(pairs)) == key_lint.py page_h32 ?
const fs = require('fs')
const d = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const h32 = s => { let h = 0; for (let i = 0; i < s.length; i++) h = ((Math.imul(h, 31) + s.charCodeAt(i)) >>> 0); return h }
const canon = v => Array.isArray(v) ? '[' + v.map(canon).join(',') + ']'
  : (v && typeof v === 'object') ? '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}'
  : JSON.stringify(v)
const got = h32(canon(d.pairs))
console.log(JSON.stringify({ arm: d.arm, n: d.n, file_page_h32: d.page_h32, node_h32: got, match: got === d.page_h32 }))

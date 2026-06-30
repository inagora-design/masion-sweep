'use strict';
// Shared static request handler. Used by:
//   - server.js          (local / any Node host, via http.createServer)
//   - api/index.js       (Vercel Serverless Function — dynamic hosting)
const fs = require('fs');
const path = require('path');

const ENTRY = "sweep sotheby's.dc.html";       // main app, served at "/"
const STANDALONE = 'sweep-standalone.dc.html'; // served at "/standalone"

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif',
  '.ico': 'image/x-icon', '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.woff': 'font/woff', '.woff2': 'font/woff2',
};

// Returns an (req, res) handler that serves files from `root`.
function createHandler(root) {
  root = path.resolve(root);
  return function handler(req, res) {
    let urlPath;
    try {
      urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    } catch {
      res.writeHead(400); return res.end('Bad Request');
    }
    if (urlPath === '/' || urlPath === '') urlPath = '/' + ENTRY;
    else if (urlPath === '/standalone') urlPath = '/' + STANDALONE;

    const filePath = path.normalize(path.join(root, urlPath));
    if (filePath !== root && !filePath.startsWith(root + path.sep)) {
      res.writeHead(403); return res.end('Forbidden');
    }
    fs.stat(filePath, (err, stat) => {
      if (err || !stat.isFile()) {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
        return res.end('Not Found');
      }
      const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'public, max-age=300' });
      fs.createReadStream(filePath).pipe(res);
    });
  };
}

module.exports = { createHandler, ENTRY, STANDALONE };

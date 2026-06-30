#!/usr/bin/env node
'use strict';
const http = require('http');
const { createHandler } = require('./lib/static');

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';

http.createServer(createHandler(__dirname)).listen(PORT, HOST, () => {
  console.log(`Sweep Sotheby's running at http://localhost:${PORT}/`);
});

'use strict';
const path = require('path');
const { createHandler } = require('../lib/static');
// On Vercel the deployed project files live at the function's parent dir.
module.exports = createHandler(path.join(__dirname, '..'));

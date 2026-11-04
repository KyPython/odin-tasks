'use strict';

// Pa11y CI resolves reporter modules by filename, then calls this factory.
module.exports = options => ({
  begin: options.onBegin,
  results: options.onResults,
  error: options.onError
});

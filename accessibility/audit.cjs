'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PUBLIC_ROUTES = ['/', '/privacy', '/terms'];
const USAGE = 'npm run audit -- --base-url http://127.0.0.1:3000 [--output results/audit.json]\n' +
  'Or: npm run audit -- --url http://127.0.0.1:3000/page [--url URL] [--allow-external]';

function validateUrl(value, allowExternal = false) {
  let url;
  try { url = new URL(value); } catch { throw new Error(`Invalid URL: ${value}`); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new Error('Use an HTTP(S) URL without embedded credentials.');
  }
  const hostname = url.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  const loopback = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
  if (!loopback && !allowExternal) {
    throw new Error('Non-loopback targets require --allow-external.');
  }
  return url.href;
}

function parseArgs(argv) {
  const options = { urls: [], allowExternal: false, output: 'results/audit.json' };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--allow-external') { options.allowExternal = true; continue; }
    if (arg === '--help') { options.help = true; continue; }
    if (!['--url', '--base-url', '--output', '--browser'].includes(arg)) {
      throw new Error(`Unknown option: ${arg}`);
    }
    const value = argv[++i];
    if (!value || value.startsWith('--')) { throw new Error(`Missing value for ${arg}`); }
    if (arg === '--url') { options.urls.push(value); }
    if (arg === '--base-url') { options.baseUrl = value; }
    if (arg === '--output') { options.output = value; }
    if (arg === '--browser') { options.browser = value; }
  }
  if (options.help) { return options; }
  if (options.baseUrl && options.urls.length) {
    throw new Error('Choose --base-url or --url, rather than combining both.');
  }
  if (options.baseUrl) {
    const base = new URL(validateUrl(options.baseUrl, options.allowExternal));
    if (base.pathname !== '/' || base.search || base.hash) {
      throw new Error('--base-url must be an origin, for example http://127.0.0.1:3000.');
    }
    options.urls = PUBLIC_ROUTES.map(route => new URL(route, base).href);
  }
  if (!options.urls.length) { throw new Error(USAGE); }
  options.urls = options.urls.map(url => validateUrl(url, options.allowExternal));
  return options;
}

function browserPath(explicit) {
  if (explicit) { return explicit; }
  if (process.env.PUPPETEER_EXECUTABLE_PATH) { return process.env.PUPPETEER_EXECUTABLE_PATH; }
  const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  return process.platform === 'darwin' && fs.existsSync(chrome) ? chrome : undefined;
}

async function audit(urls, options = {}) {
  if (!Array.isArray(urls) || !urls.length) { throw new Error('At least one URL is required.'); }
  urls = urls.map(url => validateUrl(url, options.allowExternal));
  const run = options.engine || require('pa11y-ci');
  const executionErrors = [];
  let requestedUrl;
  const reporter = {
    begin(url) { requestedUrl = url; },
    results(result) {
      if (result.pageUrl !== requestedUrl) {
        throw new Error('The browser ended at a different URL; the requested page was not audited.');
      }
    },
    error(error, url) {
      executionErrors.push({ url, name: error.name || 'Error', message: error.message || String(error) });
    }
  };
  const executablePath = browserPath(options.browser);
  const raw = await run(urls, {
    runners: [require.resolve('./readiness.cjs'), 'axe'],
    standard: 'WCAG2AA',
    threshold: 0,
    timeout: options.timeout || 15000,
    wait: 0,
    concurrency: 1,
    useIncognitoBrowserContext: true,
    reporters: [[require.resolve('./reporter.cjs'), {
      onBegin: reporter.begin, onResults: reporter.results, onError: reporter.error
    }]],
    chromeLaunchConfig: {
      ...(executablePath ? { executablePath } : {}),
      args: ['--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run']
    }
  });
  if (!raw || raw.total !== urls.length || !Number.isInteger(raw.passes) || raw.passes < 0 ||
      raw.passes > raw.total || !Number.isInteger(raw.errors) || raw.errors < 0 ||
      !raw.results || typeof raw.results !== 'object' || Array.isArray(raw.results) ||
      Object.keys(raw.results).length !== new Set(urls).size ||
      urls.some(url => !Object.hasOwn(raw.results, url) || !Array.isArray(raw.results[url]))) {
    throw new Error('Pa11y CI did not return a complete report.');
  }
  const passed = executionErrors.length === 0 && raw.errors === 0 && raw.passes === raw.total;
  return {
    passed,
    checkedAt: new Date().toISOString(),
    runner: 'axe',
    scope: options.baseUrl ? 'zeroapi-public-routes' : 'explicit-urls',
    requestedUrls: urls,
    total: raw.total,
    passes: raw.passes,
    accessibilityErrors: raw.errors,
    executionFailures: executionErrors.length,
    executionErrors,
    results: JSON.parse(JSON.stringify(raw.results, (_key, value) => value instanceof Error
      ? { name: value.name, message: value.message } : value))
  };
}

async function main(argv) {
  const options = parseArgs(argv);
  if (options.help) { console.log(USAGE); return 0; }
  const report = await audit(options.urls, options);
  const output = path.resolve(options.output);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`${report.passed ? 'PASS' : 'FAIL'}: ${report.passes}/${report.total} page attempts passed; ` +
    `${report.accessibilityErrors} accessibility errors; ${report.executionFailures} execution failures.\n${output}`);
  return report.passed ? 0 : 2;
}

if (require.main === module) {
  main(process.argv.slice(2)).then(code => { process.exitCode = code; }).catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}

module.exports = { audit, parseArgs, validateUrl };

'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');
const { test } = require('node:test');
const { audit, parseArgs } = require('../audit.cjs');

test('explicit public target has exactly the documented routes', () => {
  assert.deepEqual(parseArgs(['--base-url', 'http://127.0.0.1:3000']).urls, [
    'http://127.0.0.1:3000/', 'http://127.0.0.1:3000/privacy', 'http://127.0.0.1:3000/terms'
  ]);
});

test('invalid, credential-bearing, accidental external, and ambiguous targets fail early', async () => {
  for (const args of [[], ['--url', 'file:///tmp/index.html'], ['--url', 'not-a-url'],
    ['--url', 'https://example.com'], ['--url', 'http://name:password@localhost/'],
    ['--url'], ['--unknown'], ['--base-url', 'http://localhost/nested'],
    ['--base-url', 'http://localhost', '--url', 'http://localhost/other']]) {
    assert.throws(() => parseArgs(args));
  }
  assert.deepEqual(parseArgs(['--url', 'https://example.com', '--allow-external']).urls,
    ['https://example.com/']);
  let invoked = false;
  await assert.rejects(audit(['https://example.com'], { engine: () => { invoked = true; } }));
  assert.equal(invoked, false);
});

test('attempt failures survive a later successful result for the same URL', async () => {
  const url = 'http://127.0.0.1:3000/';
  const report = await audit([url, url], { engine: async (_urls, options) => {
    const [reporterPath, reporterOptions] = options.reporters[0];
    await require(reporterPath)(reporterOptions).error(new Error('first attempt failed'), url);
    return { total: 2, passes: 1, errors: 0, results: { [url]: [] } };
  } });
  assert.equal(report.passed, false);
  assert.equal(report.executionFailures, 1);
  assert.match(report.executionErrors[0].message, /first attempt/);
  assert.deepEqual(report.results[url], []);
});

test('an absent or incomplete engine report is a failure', async () => {
  await assert.rejects(audit(['http://localhost/'], { engine: async () => undefined }), /complete report/);
  await assert.rejects(audit(['http://localhost/'], {
    engine: async () => ({ total: 0, passes: 0, errors: 0, results: {} })
  }), /complete report/);
  for (const results of [{}, [], { 'http://localhost/': null }, { 'http://localhost/login': [] }]) {
    await assert.rejects(audit(['http://localhost/'], {
      engine: async () => ({ total: 1, passes: 1, errors: 0, results })
    }), /complete report/);
  }
});

test('real browser controls distinguish accessible HTML, findings, and an untested page', async t => {
  const server = http.createServer((request, response) => {
    response.setHeader('Content-Type', 'text/html; charset=utf-8');
    if (request.url === '/404') { response.statusCode = 404; }
    if (request.url === '/500') { response.statusCode = 500; }
    if (request.url === '/redirect') {
      response.statusCode = 302;
      response.setHeader('Location', '/login');
    }
    const content = request.url === '/bad'
      ? '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA="><button></button>'
      : '<p>A local synthetic fixture.</p><button type="button">Continue</button>';
    response.end(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Audit control</title></head><body><main><h1>Audit control</h1>${content}</main></body></html>`);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  const good = await audit([`${base}/good`], { timeout: 10000 });
  assert.equal(good.passed, true);
  assert.equal(good.accessibilityErrors, 0);
  const bad = await audit([`${base}/bad`], { timeout: 10000 });
  assert.equal(bad.passed, false);
  const codes = Object.values(bad.results).flat().map(issue => issue.code);
  assert.ok(codes.includes('image-alt'), 'real axe finds image without alternate text');
  assert.ok(codes.includes('button-name'), 'real axe finds unnamed button');

  for (const route of ['/404', '/500', '/redirect']) {
    const unready = await audit([`${base}${route}`], { timeout: 10000 });
    assert.equal(unready.passed, false, `must reject ${route} instead of auditing its accessible fallback`);
    assert.equal(unready.executionFailures, 1);
  }

  const reservation = http.createServer();
  await new Promise(resolve => reservation.listen(0, '127.0.0.1', resolve));
  const unusedPort = reservation.address().port;
  await new Promise(resolve => reservation.close(resolve));
  const failed = await audit([`http://127.0.0.1:${unusedPort}/`], { timeout: 3000 });
  assert.equal(failed.passed, false);
  assert.equal(failed.executionFailures, 1);
  assert.equal(failed.accessibilityErrors, 0);
  assert.equal(failed.passes, 0);
});

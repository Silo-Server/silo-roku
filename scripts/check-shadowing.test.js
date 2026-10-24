// Tests for scripts/check-shadowing.js against scripts/check-shadowing-fixtures.
// Run with: node --test scripts/check-shadowing.test.js
const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const { findShadowing, bsFiles, filesWith } = require('./check-shadowing.js');

const FIXTURES = path.join(__dirname, 'check-shadowing-fixtures');

function hitsIn(...names) {
    const files = names.map((name) => path.join(FIXTURES, name));
    return findShadowing(files).map((hit) => `${path.basename(hit.file)}:${hit.line} ${hit.name} -> ${hit.namespace}.${hit.member}`);
}

test('catches a parameter named like a constant of its namespace (SECTION/section)', () => {
    assert.deepEqual(hitsIn('section.bs'), ['section.bs:5 section -> storage.SECTION']);
});

test('catches a class method local named like a function declared in another file (tests.json/json)', () => {
    assert.deepEqual(hitsIn('json-helper.bs', 'json-spec.bs'), ['json-spec.bs:6 json -> tests.json']);
    assert.deepEqual(hitsIn('json-spec.bs'), [], 'only the declaring file makes json a member');
});

test('catches locals, loop variables, catch variables, and parameters of nested functions in every #if branch', () => {
    assert.deepEqual(hitsIn('enclosing.bs'), [
        'enclosing.bs:13 result -> api.result',
        'enclosing.bs:14 limit -> api.response.LIMIT',
        'enclosing.bs:19 result -> api.result',
        'enclosing.bs:25 result -> api.result'
    ]);
});

test('ignores other namespaces, nested namespaces, AA members, and code outside namespaces', () => {
    assert.deepEqual(hitsIn('clean.bs'), []);
});

test('catches locals named like constants outside namespaces in their component scope, from imports and ancestors', () => {
    const hits = findShadowing(bsFiles(path.join(FIXTURES, 'components')).concat(bsFiles(path.join(FIXTURES, 'source'))), filesWith(FIXTURES, '.xml'), FIXTURES)
        .map((hit) => `${path.basename(hit.file)}:${hit.line} ${hit.name} -> ${hit.member}`);
    assert.deepEqual(hits, ['rail.bs:8 wide -> WIDE', 'rail.bs:9 gap -> GAP', 'rail.bs:10 limit -> LIMIT']);
});

test('scans directories recursively', () => {
    assert.equal(bsFiles(FIXTURES).length, 9);
});

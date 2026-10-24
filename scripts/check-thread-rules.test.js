// Tests for scripts/check-thread-rules.js against scripts/check-thread-rules-fixtures.
// Run with: node --test scripts/check-thread-rules.test.js
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const test = require('node:test');
const { findViolations, TASK_OR_MAIN_ONLY } = require('./check-thread-rules.js');

const FIXTURES = path.join(__dirname, 'check-thread-rules-fixtures');

function hits() {
    return findViolations(FIXTURES).map((hit) => `${hit.file}:${hit.line} ${hit.component} via ${hit.via.join(' -> ')}`);
}

test('catches a render-thread component calling a source function that creates roFileSystem (hardware run 25)', () => {
    assert.ok(hits().includes('source/cache.bs:5 roFileSystem via Screen (components/Screen.xml) -> components/screen.bs -> source/cache.bs'));
});

test('follows imports transitively and checks every #if branch, matching names in any case', () => {
    assert.ok(hits().includes('source/helper.bs:3 roUrlTransfer via Screen (components/Screen.xml) -> components/screen.bs -> source/cache.bs -> source/helper.bs'));
});

test('checks scripts written inside a component XML, at their XML line', () => {
    assert.ok(hits().includes('components/Inline.xml:6 roStreamSocket via Inline (components/Inline.xml)'));
});

test('leaves Tasks (directly or through another component), comments, strings, and allowed components alone, and reports a file once', () => {
    assert.equal(hits().length, 3);
});

test('lists the components Roku allows only in a Task node or the main thread', () => {
    assert.deepEqual([...TASK_OR_MAIN_ONLY.values()].sort(), ['roChannelStore', 'roDatagramSocket', 'roFileSystem', 'roSocketAddress', 'roStreamSocket', 'roUrlTransfer']);
});

test('fails from the command line on the fixtures', () => {
    const run = spawnSync(process.execPath, [path.join(__dirname, 'check-thread-rules.js'), FIXTURES], { encoding: 'utf8' });
    assert.equal(run.status, 1);
    assert.match(run.stderr, /source\/cache\.bs:5:16: CreateObject\("roFileSystem"\) runs on the render thread/);
    assert.match(run.stderr, /check-thread-rules: 3 Task- or main-only component\(s\) created on the render thread/);
});

#!/usr/bin/env node
// Fails when a script that runs on the render thread creates a component Roku
// allows only in a Task node or on the main thread (assumption AG-237).
// brs-node does not enforce Roku's thread rules, so headless tests pass where
// the device refuses: hardware run 25's app stopped four times on
// "roFilesystem: creating MAIN|TASK-only component failed on RENDER thread",
// from a source/ function the player imported. Render-thread scripts are
// those of every component under components/ that does not extend Task,
// directly or through another component: its XML's scripts, its ancestors',
// and everything they import, transitively. A file counts if any of it is in
// such a scope, whether or not the render thread calls that function, so code
// for Tasks stays in files only Tasks import. Every #if branch is checked.
// Test components (tests/components) are not shipped and are not checked.
// There are no exceptions; one would need its reason here.
//
// The list is Roku's "BrightScript support" page, which "Render thread
// restrictions" (core-concepts/threads.md) names as the list of each
// component's threads:
// https://developer.roku.com/docs/developer-program/core-concepts/scenegraph-brightscript/brightscript-support.md
// Rows it marks "Can only be used in a Task node" or "Can only be used in a
// Task node or in the main BrightScript thread". Left out: the rows it marks
// "Should only be used in a Task node" (ParseJson, ParseXml, ReadAsciiFile,
// roAudioMetadata, roImageMetadata), advice rather than a refusal, and those
// it says cannot be used in a SceneGraph application at all, another rule.
// roHttpAgent and roDeviceInfo have no row, and their own pages state no
// thread, so they are allowed.
const fs = require('fs');
const path = require('path');
const { DiagnosticSeverity, Lexer, Parser, ParseMode, TokenKind, WalkMode, createVisitor, isImportStatement, isLiteralExpression, isVariableExpression } = require('brighterscript');

const TASK_OR_MAIN_ONLY = new Map([
    ['rodatagramsocket', 'roDatagramSocket'],
    ['rofilesystem', 'roFileSystem'],
    ['rosocketaddress', 'roSocketAddress'],
    ['rostreamsocket', 'roStreamSocket'],
    ['rourltransfer', 'roUrlTransfer'],
    ['rochannelstore', 'roChannelStore']
]);

function filesWith(target, extension) {
    if (!fs.existsSync(target)) return [];
    if (fs.statSync(target).isFile()) return target.endsWith(extension) ? [target] : [];
    return fs.readdirSync(target, { withFileTypes: true })
        .sort((a, b) => a.name.localeCompare(b.name))
        .flatMap((entry) => filesWith(path.join(target, entry.name), extension));
}

// The repository path of a "pkg:/" URI, relative to root.
function fromPkg(uri, root) {
    return path.normalize(path.join(root, uri.replace(/^pkg:\//i, '')));
}

// Each component XML as { name, parent, xml, scripts, inline }: scripts are
// file paths, inline the scripts written inside the XML as { text, line },
// line the XML's line before the script's first.
function componentsOf(root) {
    return filesWith(path.join(root, 'components'), '.xml').map((xml) => {
        const text = fs.readFileSync(xml, 'utf8');
        const tag = /<component\b[^>]*>/.exec(text)?.[0] ?? '';
        const scripts = [];
        const inline = [];
        for (const m of text.matchAll(/<script\b([^>]*?)(?:\/>|>([\s\S]*?)<\/script>)/g)) {
            const uri = /\buri="([^"]+)"/.exec(m[1])?.[1];
            if (uri) scripts.push(fromPkg(uri, root));
            else if (m[2]) inline.push({ text: m[2].replace(/<!\[CDATA\[|\]\]>/g, ''), line: text.slice(0, m.index + m[0].indexOf('>') + 1).split('\n').length - 1 });
        }
        return { name: /\bname="([^"]+)"/.exec(tag)?.[1], parent: /\bextends="([^"]+)"/.exec(tag)?.[1], xml, scripts, inline };
    }).filter((component) => component.name);
}

// The file's tokens with each conditional-compilation line (#if, #else, #const,
// ...) removed, so every branch is parsed and checked.
function tokensOf(text) {
    const kept = [];
    let skipping = false;
    for (const token of Lexer.scan(text).tokens) {
        if (token.kind.startsWith('Hash')) skipping = true;
        if (token.kind === TokenKind.Newline || token.kind === TokenKind.Eof) skipping = false;
        if (!skipping) kept.push(token);
    }
    return kept;
}

// { imports, creations } of a script's text: imports as paths, creations as
// { line, column, component } for each CreateObject of a listed component.
function scan(text, label, root) {
    const parser = Parser.parse(tokensOf(text), { mode: ParseMode.BrighterScript });
    const error = parser.diagnostics.find((d) => d.severity === DiagnosticSeverity.Error);
    if (error) throw new Error(`${label}:${error.range.start.line + 1}: ${error.message} (with every #if branch kept)`);
    const creations = [];
    parser.ast.walk(createVisitor({
        CallExpression: (call) => {
            if (!isVariableExpression(call.callee) || call.callee.name.text.toLowerCase() !== 'createobject') return;
            const first = call.args[0];
            if (!isLiteralExpression(first) || first.token.kind !== TokenKind.StringLiteral) return;
            const component = TASK_OR_MAIN_ONLY.get(first.token.text.replace(/^"|"$/g, '').toLowerCase());
            if (component) creations.push({ line: call.range.start.line + 1, column: call.range.start.character + 1, component });
        }
    }), { walkMode: WalkMode.visitAllRecursive });
    const imports = parser.ast.statements.filter(isImportStatement).map((s) => fromPkg(s.filePath, root));
    return { imports, creations };
}

// Hits as { file, line, column, component, via }: via is the chain from the
// component whose XML names the first script to the file.
function findViolations(root = '.') {
    const components = new Map(componentsOf(root).map((c) => [c.name, c]));
    const ancestry = (component) => {
        const chain = [];
        for (let c = component; c && !chain.includes(c); c = components.get(c.parent)) chain.push(c);
        return chain;
    };
    const isTask = (component) => {
        const chain = ancestry(component);
        return chain[chain.length - 1].parent === 'Task';
    };
    const scanned = new Map();
    const scanFile = (file) => {
        if (!scanned.has(file)) scanned.set(file, fs.existsSync(file) ? scan(fs.readFileSync(file, 'utf8'), path.relative(root, file), root) : { imports: [], creations: [] });
        return scanned.get(file);
    };

    const hits = new Map();
    const record = (file, creation, via) => {
        const key = `${file}:${creation.line}:${creation.column}`;
        if (!hits.has(key)) hits.set(key, { file, ...creation, via });
    };
    for (const component of components.values()) {
        if (isTask(component)) continue;
        const via = new Map();
        const queue = [];
        for (const c of ancestry(component)) {
            const xml = path.relative(root, c.xml);
            const owner = `${c.name} (${xml})`;
            for (const script of c.inline) {
                for (const creation of scan(script.text, xml, root).creations) record(xml, { ...creation, line: creation.line + script.line }, [owner]);
            }
            for (const file of c.scripts) {
                if (!via.has(file)) {
                    via.set(file, [owner, path.relative(root, file)]);
                    queue.push(file);
                }
            }
        }
        while (queue.length > 0) {
            const file = queue.shift();
            const { imports, creations } = scanFile(file);
            for (const creation of creations) record(path.relative(root, file), creation, via.get(file));
            for (const next of imports) {
                if (!via.has(next)) {
                    via.set(next, [...via.get(file), path.relative(root, next)]);
                    queue.push(next);
                }
            }
        }
    }
    return [...hits.values()].sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line || a.column - b.column);
}

function main(args) {
    const hits = findViolations(args[0] ?? '.');
    for (const hit of hits) {
        console.error(`${hit.file}:${hit.line}:${hit.column}: CreateObject("${hit.component}") runs on the render thread (${hit.via.join(' -> ')}); Roku allows it only in a Task node or the main thread`);
    }
    if (hits.length > 0) {
        console.error(`check-thread-rules: ${hits.length} Task- or main-only component(s) created on the render thread`);
        process.exitCode = 1;
    }
}

module.exports = { findViolations, TASK_OR_MAIN_ONLY };

if (require.main === module) main(process.argv.slice(2));

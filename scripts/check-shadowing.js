#!/usr/bin/env node
// Fails when a parameter or local variable is named, case-insensitively, like a
// function or constant of its own namespace or of an enclosing one (assumption
// AG-39). bsc rewrites a same-namespace name to the member without a
// diagnostic, so the local silently reads a function or the constant's value.
// bsc 0.73 does not resolve enclosing namespaces' members, but they are
// checked too, so a compiler upgrade that starts resolving them cannot bring
// the bug back silently. A constant outside any namespace is inlined the same
// way into every same-named local of its component's scope: the component's
// scripts, their imports, and its ancestors' scripts (AG-74). Files under
// source/ and tests/ compile in the source scope, which has no component's
// constants. Scans source/, components/, and tests/ unless other files or
// directories are given; prints one line per hit.
const fs = require('fs');
const path = require('path');
const { DiagnosticSeverity, Lexer, Parser, ParseMode, TokenKind, WalkMode, createVisitor, isImportStatement, isNamespaceStatement, isMethodStatement } = require('brighterscript');

const DEFAULT_ROOTS = ['source', 'components', 'tests'];

function filesWith(target, extension) {
    if (fs.statSync(target).isFile()) return target.endsWith(extension) ? [target] : [];
    return fs.readdirSync(target, { withFileTypes: true })
        .sort((a, b) => a.name.localeCompare(b.name))
        .flatMap((entry) => filesWith(path.join(target, entry.name), extension));
}

const bsFiles = (target) => filesWith(target, '.bs');

// The repository path of a "pkg:/" URI, relative to root.
function fromPkg(uri, root) {
    return path.join(root, uri.replace(/^pkg:\//i, ''));
}

// Each component XML as { name, parent, scripts }, scripts being file paths.
function componentsOf(xmlFiles, root) {
    return xmlFiles.map((file) => {
        const text = fs.readFileSync(file, 'utf8');
        const tag = /<component\b[^>]*>/.exec(text)?.[0] ?? '';
        const scripts = [...text.matchAll(/<script\b[^>]*\buri="([^"]+\.bs)"/g)].map((m) => fromPkg(m[1], root));
        return { name: /\bname="([^"]+)"/.exec(tag)?.[1], parent: /\bextends="([^"]+)"/.exec(tag)?.[1], scripts };
    }).filter((component) => component.name);
}

// "a.b" for a node inside namespace a.b, or "" outside any namespace.
function namespaceOf(node) {
    const names = [];
    for (let ns = node.findAncestor(isNamespaceStatement); ns; ns = ns.parent?.findAncestor(isNamespaceStatement)) {
        names.unshift(ns.getName(ParseMode.BrighterScript));
    }
    return names.join('.').toLowerCase();
}

// "a.b" and "a" for "a.b".
function namespaceChain(ns) {
    const parts = ns.split('.');
    return parts.map((_, i) => parts.slice(0, parts.length - i).join('.'));
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

function where(file, token) {
    return `${file}:${token.range.start.line + 1}:${token.range.start.character + 1}`;
}

// Hits as { file, line, column, name, member, kind, namespace, declaredAt };
// namespace is "" for a constant outside any namespace. xmlFiles are the
// component XML files that place the constants' scripts in scopes, with
// "pkg:/" URIs resolved against root.
function findShadowing(files, xmlFiles = [], root = '.') {
    const parsed = files.map((file) => {
        const parser = Parser.parse(tokensOf(fs.readFileSync(file, 'utf8')), { mode: ParseMode.BrighterScript });
        const error = parser.diagnostics.find((d) => d.severity === DiagnosticSeverity.Error);
        if (error) throw new Error(`${file}:${error.range.start.line + 1}: ${error.message} (with every #if branch kept)`);
        return { file, ast: parser.ast };
    });

    // Namespace members by "namespace" then lowercase name.
    const members = new Map();
    const declare = (file, node, token, kind) => {
        const ns = namespaceOf(node);
        if (ns === '') return;
        if (!members.has(ns)) members.set(ns, new Map());
        const byName = members.get(ns);
        const key = token.text.toLowerCase();
        if (!byName.has(key)) byName.set(key, { name: token.text, kind, declaredAt: where(file, token) });
    };
    for (const { file, ast } of parsed) {
        ast.walk(createVisitor({
            FunctionStatement: (s) => { if (!isMethodStatement(s)) declare(file, s, s.name, 'function'); },
            ConstStatement: (s) => declare(file, s, s.tokens.name, 'constant')
        }), { walkMode: WalkMode.visitStatementsRecursive });
    }

    // Constants outside any namespace and the imports, by normalized file path.
    const globals = new Map();
    const imports = new Map();
    for (const { file, ast } of parsed) {
        const consts = new Map();
        ast.walk(createVisitor({
            ConstStatement: (s) => {
                const key = s.tokens.name.text.toLowerCase();
                if (namespaceOf(s) === '' && !consts.has(key)) consts.set(key, { name: s.tokens.name.text, kind: 'constant', declaredAt: where(file, s.tokens.name) });
            }
        }), { walkMode: WalkMode.visitStatementsRecursive });
        globals.set(path.normalize(file), consts);
        imports.set(path.normalize(file), ast.statements.filter(isImportStatement).map((s) => path.normalize(fromPkg(s.filePath, root))));
    }
    // The scripts and everything they import, transitively.
    const withImports = (scripts) => {
        const seen = new Set();
        const visit = (file) => {
            if (seen.has(file)) return;
            seen.add(file);
            for (const next of imports.get(file) ?? []) visit(next);
        };
        scripts.forEach((file) => visit(path.normalize(file)));
        return seen;
    };
    // The visible constants outside namespaces, by file: the union over each
    // component scope a file under components/ belongs to; elsewhere, the
    // file's own.
    const components = new Map(componentsOf(xmlFiles, root).map((c) => [c.name, c]));
    const inComponents = (file) => path.relative(root, file).split(path.sep)[0] === 'components';
    const visible = new Map();
    for (const component of components.values()) {
        const own = withImports(component.scripts);
        const scope = new Set(own);
        const ancestors = new Set();
        for (let parent = components.get(component.parent); parent && !ancestors.has(parent); parent = components.get(parent.parent)) {
            ancestors.add(parent);
            withImports(parent.scripts).forEach((f) => scope.add(f));
        }
        const consts = new Map();
        for (const f of scope) for (const [key, value] of globals.get(f) ?? []) if (!consts.has(key)) consts.set(key, value);
        for (const f of own) if (inComponents(f)) visible.set(f, new Map([...(visible.get(f) ?? []), ...consts]));
    }
    for (const [file, consts] of globals) {
        if (!visible.has(file)) visible.set(file, consts);
    }

    const hits = [];
    const check = (file, node, token) => {
        if (!token) return;
        const { line, character } = token.range.start;
        const hit = (member, namespace) => hits.push({ file, line: line + 1, column: character + 1, name: token.text, member: member.name, kind: member.kind, namespace, declaredAt: member.declaredAt });
        const ns = namespaceOf(node);
        if (ns !== '') {
            for (const candidate of namespaceChain(ns)) {
                const member = members.get(candidate)?.get(token.text.toLowerCase());
                if (member) return hit(member, candidate);
            }
        }
        const global = visible.get(path.normalize(file))?.get(token.text.toLowerCase());
        if (global) hit(global, '');
    };
    for (const { file, ast } of parsed) {
        ast.walk(createVisitor({
            FunctionParameterExpression: (e) => check(file, e, e.name),
            AssignmentStatement: (s) => check(file, s, s.name),
            ForEachStatement: (s) => check(file, s, s.item),
            CatchStatement: (s) => check(file, s, s.exceptionVariable)
        }), { walkMode: WalkMode.visitAllRecursive });
    }
    return hits;
}

function main(args) {
    const roots = args.length > 0 ? args : DEFAULT_ROOTS;
    const hits = findShadowing(roots.flatMap(bsFiles), roots.flatMap((root) => filesWith(root, '.xml')));
    for (const hit of hits) {
        const member = hit.namespace === '' ? hit.member : `${hit.namespace}.${hit.member}`;
        console.error(`${hit.file}:${hit.line}:${hit.column}: "${hit.name}" is the name of ${hit.kind} ${member} (${hit.declaredAt}); rename the local`);
    }
    if (hits.length > 0) {
        console.error(`check-shadowing: ${hits.length} local name(s) shadowed by namespace members or constants`);
        process.exitCode = 1;
    }
}

module.exports = { findShadowing, bsFiles, filesWith };

if (require.main === module) main(process.argv.slice(2));

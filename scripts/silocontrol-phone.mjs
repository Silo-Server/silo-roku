#!/usr/bin/env node
// A development controller that plays a Silo phone's part against the Roku's
// SiloControl receiver (docs/silocontrol.md), over plain TCP. It connects,
// answers pings, prints every frame the Roku sends as one JSON line, and
// runs the steps given after the options, in order:
//
//   wait <seconds>                 keep listening
//   hello                          send the phone hello (sent first unless
//                                  --no-hello); the server is the Roku's own
//                                  unless --server names one
//   control <name> [json]          a control command, e.g. control seek '{"seconds":60}'
//   offer <profileId> [json]       a handoff offer for the Roku's server
//   launch <contentId> [json]      a launch; json adds playback fields
//   presence <true|false>          change the passive flag
//   raw <json>                     send this envelope as it is
//   close                          send close and end
//
// With --pairing it plays a phone's part in companion sign-in instead
// (docs/companion-pairing.md): port 52827, no SiloControl hello, and the
// steps wait, raw, push <serverURL> [json] (a pushServer; json adds
// serverName, serverIdentity, endpoints), done, and cancel [reason].
//
// Options: --host (default ROKU_HOST), --port (52817, or 52827 with
// --pairing), --pairing, --name, --device-id,
// --server <url>, --passive, --no-hello, --no-pong, --features a,b, and
// --key <pairing key, hex or base32> for level sealed (section 9.2), whose
// construction this script shares with source/control/sealed.bs.
// Codes a handoff challenge carries, and resume tokens, are masked in what
// it prints. Node's standard library only, so it runs on any host that can
// reach the Roku (scripts/silocontrol-phone.sh runs it through
// ROKU_DEPLOY_VIA).
import net from 'node:net';
import crypto from 'node:crypto';

const MAX_FRAME = 1 << 20;

function parse(argv) {
    const options = { host: process.env.ROKU_HOST || '', port: 52817, name: 'Node controller', deviceId: '', server: '', passive: false, hello: true, pong: true, features: ['close_reason', 'resume_token', 'replace_confirmation'], key: '', pairing: false };
    const steps = [];
    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];
        if (arg === '--host') options.host = argv[++i];
        else if (arg === '--port') options.port = Number(argv[++i]);
        else if (arg === '--name') options.name = argv[++i];
        else if (arg === '--device-id') options.deviceId = argv[++i];
        else if (arg === '--server') options.server = argv[++i];
        else if (arg === '--passive') options.passive = true;
        else if (arg === '--no-hello') options.hello = false;
        else if (arg === '--no-pong') options.pong = false;
        else if (arg === '--features') options.features = argv[++i].split(',').filter(Boolean);
        else if (arg === '--key') options.key = argv[++i];
        else if (arg === '--pairing') options.pairing = true;
        else steps.push(arg);
    }
    if (!options.deviceId) options.deviceId = 'node-' + crypto.randomUUID();
    if (options.pairing && !argv.includes('--port')) options.port = 52827;
    return { options, steps };
}

// The phones' registry key for a server URL (ServerRegistry.serverId(for:)).
function serverIdOf(url) {
    let s = url.trim();
    while (s.endsWith('/')) s = s.slice(0, -1);
    return Buffer.from(s, 'utf8').toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ---- Level sealed (docs/silocontrol.md section 9.2)
const LABEL = 'silo-cast-sealed-1';
const FROM_PHONE = 1;
const FROM_TV = 2;
const hmac = (key, message) => crypto.createHmac('sha256', key).update(message).digest();

function keyBytes(text) {
    if (/^[0-9a-f]{32}$/i.test(text)) return Buffer.from(text, 'hex');
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    let bits = 0, value = 0;
    const out = [];
    for (const char of text.replace(/[\s=]/g, '').toUpperCase()) {
        value = (value << 5) | alphabet.indexOf(char);
        bits += 5;
        if (bits >= 8) { bits -= 8; out.push((value >> bits) & 0xff); }
    }
    return Buffer.from(out);
}

function sessionKeys(key, phoneNonce, tvNonce) {
    const prk = hmac(Buffer.concat([phoneNonce, tvNonce]), key);
    const expand = (purpose) => hmac(prk, Buffer.concat([Buffer.from(`${LABEL} ${purpose}`), Buffer.from([1])]));
    return { encKey: expand('enc').subarray(0, 16), macKey: expand('mac'), ivKey: expand('iv').subarray(0, 16) };
}

function seqBytes(seq) {
    const out = Buffer.alloc(8);
    out.writeUInt32BE(seq, 4);
    return out;
}

function seal(keys, seq, text) {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipheriv('aes-128-cbc', keys.encKey, iv);
    const signed = Buffer.concat([seqBytes(seq), iv, cipher.update(Buffer.from(text, 'utf8')), cipher.final()]);
    return Buffer.concat([signed, hmac(keys.macKey, Buffer.concat([Buffer.from(LABEL), Buffer.from([FROM_PHONE]), signed]))]);
}

function open(keys, seq, body) {
    const signed = body.subarray(0, body.length - 32);
    const tag = hmac(keys.macKey, Buffer.concat([Buffer.from(LABEL), Buffer.from([FROM_TV]), signed]));
    if (!crypto.timingSafeEqual(tag, body.subarray(body.length - 32))) throw new Error('frame tag mismatch');
    if (!signed.subarray(0, 8).equals(seqBytes(seq))) throw new Error(`frame out of order (wanted ${seq})`);
    const decipher = crypto.createDecipheriv('aes-128-cbc', keys.encKey, signed.subarray(8, 24));
    return Buffer.concat([decipher.update(signed.subarray(24)), decipher.final()]).toString('utf8');
}

function envelope(type, key, payload) {
    const out = { type, v: 2 };
    if (key) out[key] = payload;
    return out;
}

function mask(message) {
    const copy = JSON.parse(JSON.stringify(message));
    const challenge = copy.handoffChallenge;
    if (challenge) {
        if (challenge.userCode) challenge.userCode = '********';
        if (challenge.matchCode) challenge.matchCode = '****';
    }
    for (const payload of [copy.handoffReady, copy.handoffOffer]) {
        if (payload && payload.resumeToken) payload.resumeToken = '<resumeToken>';
    }
    if (copy.type === 'deviceStarted') {
        if (copy.userCode) copy.userCode = '********';
        if (copy.matchCode) copy.matchCode = '****';
    }
    return copy;
}

function keyIdOf(key) {
    return crypto.createHash('sha256').update(key).digest('hex').slice(0, 8);
}

function json(text, fallback) {
    if (text === undefined) return fallback;
    return JSON.parse(text);
}

async function main() {
    const { options, steps } = parse(process.argv.slice(2));
    if (!options.host) throw new Error('no host: pass --host or set ROKU_HOST');
    const socket = net.connect({ host: options.host, port: options.port });
    let pending = Buffer.alloc(0);
    let tvHello = null;
    // Level sealed: the key, this side's nonce, and once keyed the session.
    const sealed = options.key ? { key: keyBytes(options.key), nonce: crypto.randomBytes(16), keys: null, sendSeq: 0, recvSeq: 0 } : null;
    let closed = false;
    const waiters = [];
    const started = Date.now();

    const log = (direction, message) => {
        const t = ((Date.now() - started) / 1000).toFixed(2);
        process.stdout.write(`${t} ${direction} ${JSON.stringify(mask(message))}\n`);
    };
    const send = (message, plain = false) => {
        if (sealed && !sealed.keys && !plain) throw new Error('sealed handshake incomplete');
        let body = Buffer.from(JSON.stringify(message), 'utf8');
        if (sealed && !plain) body = seal(sealed.keys, sealed.sendSeq++, JSON.stringify(message));
        const head = Buffer.alloc(4);
        head.writeUInt32BE(body.length);
        socket.write(Buffer.concat([head, body]));
        log('>>', message);
    };

    socket.on('data', (chunk) => {
        pending = Buffer.concat([pending, chunk]);
        while (pending.length >= 4) {
            const size = pending.readUInt32BE(0);
            if (size > MAX_FRAME) throw new Error('frame too large');
            if (pending.length < 4 + size) break;
            const raw = pending.subarray(4, 4 + size);
            pending = pending.subarray(4 + size);
            let message;
            if (sealed && sealed.keys) message = JSON.parse(open(sealed.keys, sealed.recvSeq++, raw));
            else message = JSON.parse(raw.toString('utf8'));
            if (sealed && !sealed.keys) {
                log('<<', message);
                // Before the keys only the Roku's sealed_hello for this key
                // may come; anything else is a refusal or a downgrade.
                if (message.type !== 'sealed_hello' || message.keyId !== keyIdOf(sealed.key)) {
                    socket.destroy();
                    return;
                }
                sealed.keys = sessionKeys(sealed.key, sealed.nonce, Buffer.from(message.nonce, 'base64url'));
                for (const waiter of waiters.splice(0)) waiter();
                continue;
            }
            log('<<', message);
            if (message.type === 'hello') tvHello = options.pairing ? message : message.hello;
            if (message.type === 'ping' && options.pong) send(envelope('pong'));
            for (const waiter of waiters.splice(0)) waiter();
        }
    });
    socket.on('close', () => {
        closed = true;
        log('--', { closed: true });
        for (const waiter of waiters.splice(0)) waiter();
    });
    socket.on('error', (error) => log('--', { error: error.message }));

    await new Promise((resolve, reject) => {
        socket.once('connect', resolve);
        socket.once('error', reject);
    });
    log('--', { connected: `${options.host}:${options.port}` });
    if (sealed) {
        send({ type: 'sealed_hello', v: 1, keyId: keyIdOf(sealed.key), nonce: sealed.nonce.toString('base64url') }, true);
    }
    const until = (test, ms) => new Promise((resolve) => {
        const deadline = setTimeout(resolve, ms);
        const check = () => {
            if (test() || closed) {
                clearTimeout(deadline);
                resolve();
            } else waiters.push(check);
        };
        check();
    });
    await until(() => tvHello !== null, 5000);
    const serverId = () => (options.server ? serverIdOf(options.server) : tvHello?.serverId || '');
    const hello = () => send(envelope('hello', 'hello', {
        role: 'phone', deviceName: options.name, deviceId: options.deviceId, serverId: serverId(),
        serverName: tvHello?.serverName ?? null, supportedVersions: [2], features: options.features,
        ...(options.passive ? { passive: true } : {}),
    }));
    if (options.hello && !options.pairing) hello();
    const pairing = (type, fields = {}) => send({ type, v: 1, ...fields });

    for (let i = 0; i < steps.length && !closed; i++) {
        const step = steps[i];
        if (step === 'wait') await until(() => false, Number(steps[++i]) * 1000);
        else if (step === 'hello') hello();
        else if (step === 'control') {
            const name = steps[++i];
            const args = steps[i + 1]?.startsWith('{') ? json(steps[++i]) : {};
            send(envelope('control', 'control', { name, ...args }));
        } else if (step === 'offer') {
            const profileId = steps[++i];
            const extra = steps[i + 1]?.startsWith('{') ? json(steps[++i]) : {};
            const url = options.server || tvHello?.serverId && Buffer.from(tvHello.serverId.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8');
            send(envelope('handoff_offer', 'handoffOffer', { requestId: crypto.randomUUID(), serverId: serverId(), serverURL: url || '', serverName: tvHello?.serverName ?? null, profileId, ...extra }));
        } else if (step === 'launch') {
            const contentId = steps[++i];
            const extra = steps[i + 1]?.startsWith('{') ? json(steps[++i]) : {};
            send(envelope('launch', 'launch', { serverId: serverId(), playback: { contentId, startFromBeginning: false, ...extra } }));
        } else if (step === 'presence') send(envelope('presence', 'presence', { passive: steps[++i] === 'true' }));
        else if (step === 'raw') send(json(steps[++i]));
        else if (step === 'push') {
            const serverURL = steps[++i];
            const extra = steps[i + 1]?.startsWith('{') ? json(steps[++i]) : {};
            pairing('pushServer', { serverURL, ...extra });
        } else if (step === 'done') pairing('done');
        else if (step === 'cancel') pairing('cancel', { reason: steps[i + 1] && !['wait', 'push', 'done', 'raw'].includes(steps[i + 1]) ? steps[++i] : 'cancelled' });
        else if (step === 'close') {
            send(envelope('close', 'close', { reason: 'replaced' }));
            await until(() => false, 300);
            socket.end();
        } else throw new Error(`unknown step ${step}`);
    }
    socket.end();
}

main().catch((error) => {
    process.stderr.write(`silocontrol-phone: ${error.message}\n`);
    process.exit(1);
});

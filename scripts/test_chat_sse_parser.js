#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'js', 'chat_sse.js'), 'utf8');
const wrapped = src
    .replace('(function (global)', '(function (global)')
    .replace('})(typeof window !== \'undefined\' ? window : this);', '})(globalThis);');
eval(wrapped);

const parse = globalThis.ChatSSE.parseSseChunk;

const partial = [
    'id: done',
    'event: done',
    'data: {"status":"ok","message_count":2}',
].join('\n');
const flushed = parse(partial, { forceFlush: true });
if (!flushed.events.length || flushed.events[0].event !== 'done') {
    console.error('FAIL: forceFlush did not parse trailing done event');
    process.exit(1);
}

const normal = parse('event: status\ndata: {"label":"processing"}\n\nid: done\nevent: done\ndata: {"ok":1}\n\n');
if (normal.events.length !== 2) {
    console.error('FAIL: expected 2 events, got', normal.events.length);
    process.exit(1);
}

console.log('chat_sse parser tests PASS');

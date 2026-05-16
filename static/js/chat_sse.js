/**
 * チャット SSE クライアント（POST /api/chat/stream）
 */
(function (global) {
    'use strict';

    function parseSseChunk(buffer) {
        const events = [];
        const parts = buffer.split('\n\n');
        const rest = parts.pop() || '';
        parts.forEach(function (block) {
            if (!block.trim()) return;
            let event = 'message';
            let id = null;
            let data = '';
            block.split('\n').forEach(function (line) {
                if (line.indexOf('event:') === 0) event = line.slice(6).trim();
                else if (line.indexOf('id:') === 0) id = line.slice(3).trim();
                else if (line.indexOf('data:') === 0) data += line.slice(5).trim();
            });
            if (data) {
                try {
                    events.push({ event: event, id: id, data: JSON.parse(data) });
                } catch (e) {
                    events.push({ event: event, id: id, data: { raw: data } });
                }
            }
        });
        return { events: events, rest: rest };
    }

    function submitStream(options) {
        const url = options.url || '/api/chat/stream';
        const message = options.message;
        const withVersion = options.withVersion || function (p) { return p; };
        const onEvent = options.onEvent || function () {};
        const onDone = options.onDone || function () {};
        const onError = options.onError || function () {};

        const formData = new FormData();
        formData.append('message', message);

        const headers = { 'Cache-Control': 'no-cache', Accept: 'text/event-stream' };
        if (options.lastEventId) {
            headers['Last-Event-ID'] = String(options.lastEventId);
        }

        return fetch(withVersion(url), {
            method: 'POST',
            credentials: 'include',
            body: formData,
            headers: headers,
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('SSE HTTP ' + response.status);
            }
            if (!response.body || !response.body.getReader) {
                throw new Error('SSE stream not supported');
            }
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let lastEventId = null;
            let lastDonePayload = null;

            function pump() {
                return reader.read().then(function (result) {
                    if (result.done) {
                        onDone({ lastEventId: lastEventId, done: lastDonePayload });
                        return;
                    }
                    buffer += decoder.decode(result.value, { stream: true });
                    const parsed = parseSseChunk(buffer);
                    buffer = parsed.rest;
                    parsed.events.forEach(function (ev) {
                        if (ev.id) lastEventId = ev.id;
                        if (ev.event === 'done' && ev.data) {
                            lastDonePayload = ev.data;
                        }
                        onEvent(ev);
                    });
                    return pump();
                });
            }
            return pump();
        }).catch(function (err) {
            onError(err);
        });
    }

    global.ChatSSE = {
        submitStream: submitStream,
        parseSseChunk: parseSseChunk,
    };
})(typeof window !== 'undefined' ? window : this);

/**
 * チャット SSE クライアント（POST /api/chat/stream）
 */
(function (global) {
    'use strict';

    function parseSseChunk(buffer, options) {
        const opts = options || {};
        const events = [];
        const parts = buffer.split('\n\n');
        const rest = opts.forceFlush ? '' : (parts.pop() || '');
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
        if (opts.forceFlush && rest.trim()) {
            const tail = parseSseChunk(rest + '\n\n', { forceFlush: false });
            tail.events.forEach(function (ev) {
                events.push(ev);
            });
        }
        return { events: events, rest: rest };
    }

    function consumeSseEvents(buffer, onChunk, forceFlush) {
        const parsed = parseSseChunk(buffer, { forceFlush: forceFlush });
        parsed.events.forEach(onChunk);
        return parsed.rest;
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

        const fetchOpts = {
            method: 'POST',
            credentials: 'include',
            body: formData,
            headers: headers,
        };
        if (options.signal) {
            fetchOpts.signal = options.signal;
        }

        return fetch(withVersion(url), fetchOpts).then(function (response) {
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

            function trackEvent(ev) {
                if (ev.id) lastEventId = ev.id;
                if (ev.event === 'done' && ev.data) {
                    lastDonePayload = ev.data;
                }
                onEvent(ev);
            }

            function pump() {
                return reader.read().then(function (result) {
                    if (result.done) {
                        // Safari may close the stream before a trailing blank line arrives.
                        if (buffer) {
                            buffer = consumeSseEvents(buffer, trackEvent, true);
                        }
                        onDone({ lastEventId: lastEventId, done: lastDonePayload });
                        return;
                    }
                    buffer += decoder.decode(result.value, { stream: true });
                    buffer = consumeSseEvents(buffer, trackEvent, false);
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
        consumeSseEvents: consumeSseEvents,
    };
})(typeof window !== 'undefined' ? window : this);

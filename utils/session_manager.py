from collections.abc import MutableMapping
from threading import local
from flask import session as flask_session, has_request_context

class RequestSafeSession(MutableMapping):
    """Flaskセッションをリクエストコンテキスト外でも安全に扱うためのラッパー"""

    def __init__(self):
        self._storage = local()

    def _use_real_session(self) -> bool:
        return has_request_context()

    def _fallback_store(self):
        if not hasattr(self._storage, 'data'):
            self._storage.data = {}
            self._storage.modified = False
        return self._storage

    def __getitem__(self, key):
        if self._use_real_session():
            return flask_session[key]
        store = self._fallback_store()
        return store.data[key]

    def __setitem__(self, key, value):
        if self._use_real_session():
            flask_session[key] = value
        else:
            store = self._fallback_store()
            store.data[key] = value
            store.modified = True

    def __delitem__(self, key):
        if self._use_real_session():
            del flask_session[key]
        else:
            store = self._fallback_store()
            del store.data[key]
            store.modified = True

    def __iter__(self):
        if self._use_real_session():
            return iter(flask_session)
        return iter(self._fallback_store().data)

    def __len__(self):
        if self._use_real_session():
            return len(flask_session)
        return len(self._fallback_store().data)

    def get(self, key, default=None):
        if self._use_real_session():
            return flask_session.get(key, default)
        return self._fallback_store().data.get(key, default)

    def setdefault(self, key, default=None):
        if self._use_real_session():
            return flask_session.setdefault(key, default)
        store = self._fallback_store()
        if key not in store.data:
            store.data[key] = default
            store.modified = True
        return store.data[key]

    def pop(self, key, default=None):
        if self._use_real_session():
            return flask_session.pop(key, default)
        store = self._fallback_store()
        store.modified = True
        return store.data.pop(key, default)

    def clear(self):
        if self._use_real_session():
            flask_session.clear()
        else:
            store = self._fallback_store()
            store.data.clear()
            store.modified = True

    @property
    def modified(self):
        if self._use_real_session():
            return flask_session.modified
        return self._fallback_store().modified

    @modified.setter
    def modified(self, value: bool):
        if self._use_real_session():
            flask_session.modified = value
        else:
            store = self._fallback_store()
            store.modified = bool(value)

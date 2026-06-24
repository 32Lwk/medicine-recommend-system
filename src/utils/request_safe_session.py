"""
リクエスト単位のミュータブルセッション状態（Flask session 非依存）

FastAPI では都度新規インスタンスを生成し、DB・Cookie（sid）と整合させる。
"""

from collections.abc import MutableMapping


class _PopMissing:
    pass


_POP_MISSING = _PopMissing()


class RequestSafeSession(MutableMapping):
    """dict + modified フラグ。ネストした list の in-place 変更後は呼び出し側で modified を立てる。"""

    __slots__ = ("_store", "_modified")

    def __init__(self, initial=None):
        self._store = dict(initial or {})
        self._modified = False

    @property
    def modified(self) -> bool:
        return self._modified

    @modified.setter
    def modified(self, value: bool):
        self._modified = bool(value)

    def __getitem__(self, key):
        return self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value
        self._modified = True

    def __delitem__(self, key):
        del self._store[key]
        self._modified = True

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def get(self, key, default=None):
        return self._store.get(key, default)

    def setdefault(self, key, default=None):
        if key not in self._store:
            self._store[key] = default
            self._modified = True
        return self._store[key]

    def pop(self, key, default=_POP_MISSING):
        if key in self._store:
            self._modified = True
            return self._store.pop(key)
        if default is not _POP_MISSING:
            return default
        raise KeyError(key)

    def clear(self):
        self._store.clear()
        self._modified = True

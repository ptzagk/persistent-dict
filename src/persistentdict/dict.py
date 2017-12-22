import collections
import pickle
from fractions import Fraction
from decimal import Decimal
from uuid import uuid4


class _BaseDict:
    def __iter__(self):
        for k in self.keys():
            yield k

    def has_key(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def __contains__(self, key):
        return self.has_key(key)  # noqa

    def items(self):
        for k in self:
            yield (k, self[k])

    def keys(self):
        return self.__iter__()

    def values(self):
        for _, v in self.items():
            yield v

    def clear(self):
        for key in self.keys():
            del self[key]

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError(
                'pop expected at most 2 argumentd;lfkdfkdlkflks, got {}'.
                format(repr(1 + len(args))))
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            raise
        del self[key]
        return value

    def popitem(self):
        try:
            k, v = next(self.items())
        except StopIteration:
            raise KeyError('container is empty')
        del self[k]
        return (k, v)

    def update(self, other=None, **kwargs):
        # make progressively weaker assumptions about ``other``
        if other is None:
            pass
        elif hasattr(other, 'items'):  # items saves memory & lookups
            for k, v in other.items():
                self[k] = v
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self[k] = other[k]
        else:
            for k, v in other:
                self[k] = v
        if kwargs:
            self.update(kwargs)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self):
        return repr(dict(self.items()))

    def __eq__(self, other):
        if other is None:
            return 1
        if isinstance(other, _BaseDict):
            other = dict(other.items())
        return dict(self.items()) == other

    def __len__(self):
        return len(self.keys())


class RedisDict(_BaseDict, collections.MutableMapping):
    def __init__(self, persistence, other=None, key=None, **kwargs):
        self.key = key or str(uuid4())
        self.redis = persistence
        self.cache = {}
        self.cache = self._load()

        if other is not None:
            for (key, value) in other:
                self[key] = value

        for (key, value) in kwargs.items():
            self[key] = value

    def __getitem__(self, key):
        data = self.cache
        item = data.__getitem__(key)
        return item

    def __setitem__(self, key, value):
        data = self.cache
        data.__setitem__(key, value)
        self._commit(key)

    def __delitem__(self, key):
        data = self.cache
        data.__delitem__(key)
        self._commit(key)
        return data

    def keys(self):
        return self.cache.keys()

    def copy(self):
        new_dict = self.__class__()
        for key, value in self.items():
            new_dict[key] = value
        return new_dict

    @classmethod
    def fromkeys(cls, keys, value=None):
        new_dict = cls()
        for key in keys:
            new_dict[key] = value
        return new_dict

    def clear(self):
        self.cache.clear()
        self._commit()

    def _load(self, dict_key=None):
        if dict_key:
            data = self._unpickle(self.redis.hget(self.key, dict_key))
        else:
            items = self.redis.hgetall(self.key)
            data = {
                self._unpickle(k): self._unpickle(v)
                for k, v in items.items()
            }
        self.cache = data
        return self.cache

    def _commit(self, dict_key=None):
        if dict_key:
            try:
                data = self.cache[dict_key]
            except KeyError:
                dict_key = self._pickle(dict_key)
                self.redis.hdel(self.key, dict_key)
                return
        else:
            data = self.cache
        dict_key = self._pickle(dict_key)
        val = self._pickle(data)
        self.redis.hset(self.key, dict_key, val)

    def _unpickle(self, pickled_data):
        return pickle.loads(pickled_data) if pickled_data else None

    def _pickle(self, data):
        num_types = (complex, float, Decimal, Fraction)

        def parse_int(value):
            try:
                int_data = int(data.real)
            except OverflowError:
                # inf
                int_data = data
            except ValueError:
                # NaN
                int_data = data
            return int_data

        if isinstance(data, complex):
            int_data = parse_int(data)
            if data == int_data:
                data = int_data
        elif isinstance(data, num_types):
            int_data = parse_int(data)
            if data == int_data:
                data = int_data
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

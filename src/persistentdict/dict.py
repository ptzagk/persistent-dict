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
                'pop expected at most 2 argumentds, got {}'.
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
        self._key = key or str(uuid4())
        self._redis = persistence
        self._cache = {}

        if other is not None:
            for (key, value) in other:
                self[key] = value

        for (key, value) in kwargs.items():
            self[key] = value

    def __getitem__(self, key):
        try:
            value = self._cache[key]
        except KeyError:
            value = self._backend_get(key=key)
        self._cache[key] = value
        return value

    def __setitem__(self, key, value):
        self._backend_set(key=key, value=value)
        self._cache[key] = value

    def __delitem__(self, key):
        if not self._backend_del(key):
            raise KeyError(key)
        self._cache.__delitem__(key)

    def keys(self):
        return list(self.__iter__())

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
        self._backend_clear()
        self._cache.clear()

    def __iter__(self, pipe=None):
        for key in self._backend_load(self._redis).keys():
            yield key

    def __contains__(self, key):
        return self._backend_key_exists(key)

    def _backend_load(self, pipe=None):
        return {
            self._unpickle(k): self._unpickle(v)
            for k, v in self._redis.hgetall(self._key).items()
        }

    def _backend_clear(self):
        self._redis.delete(self._key)

    def _backend_key_exists(self, key):
        return bool(self._redis.hexists(self._key, self._pickle(key)))

    def _backend_del(self, key):
        number_deleted = self._redis.hdel(self._key, self._pickle(key))
        return bool(number_deleted > 0)

    def _backend_set(self, key, value):
        self._redis.hset(self._key, self._pickle(key), self._pickle(value))

    def _backend_get(self, key):
        pickled_value = self._redis.hget(self._key, self._pickle(key))
        if pickled_value is None:
            raise KeyError(key)
        return self._unpickle(pickled_value)

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

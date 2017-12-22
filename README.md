# persistent-dict

A Python Dict which stores data in Redis.

## Installation

To install, simply:

```bash
pip install persistent-dict
```

## How to use

```python
import redis
from persistentdict import RedisDict

mydict = RedisDict(persistence=redis.StrictRedis())

# with a specific storage key in redis
mydict = RedisDict(persistence=redis.StrictRedis(), key='stuff')

mydict['hello'] = 'world'

print(mydict)
{'hello': 'world'}
```

## Tips

- You can use ``RedisDict`` exactly like a normal ``dict``. As long as all the keys and values in it are [picklable](https://docs.python.org/3/library/pickle.html).
- When first instantiated, data will be populated into an in-memory cache. When updates are performed both the in-memory cache and Redis will be kept in sync with each other.

## Future plans

- Support for other storage backends other than Redis.

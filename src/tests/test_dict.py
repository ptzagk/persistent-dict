import uuid

from hypothesis import given
from hypothesis import strategies as st
import pytest
import fakeredis

from persistentdict import RedisDict

DICT_CONTEXT_STRAT = (st.booleans() | st.datetimes() | st.text()
                      | st.integers() | st.dates() | st.times()
                      | st.timedeltas() | st.uuids() | st.characters())


@pytest.fixture
def redis():
    return fakeredis.FakeStrictRedis()


@pytest.fixture
def key():
    return str(uuid.uuid4())


@pytest.fixture
def redisdict(redis, key):
    return RedisDict(persistence=redis, key=key)


@given(key=DICT_CONTEXT_STRAT, val=DICT_CONTEXT_STRAT)
def test_persist_different_types_of_data(redisdict, key, val):
    redisdict.clear()
    redisdict[key] = val

    try:
        assert redisdict[key] == val
    except AssertionError:
        if (isinstance(val, complex) and isinstance(redisdict[key], complex)):
            # nanj cannot be compared
            assert str(redisdict[key]) == str(val)
        else:
            raise
    assert list(redisdict.keys()) == [key]
    assert list(redisdict.values()) == [val]


def test_keys(redisdict):
    redisdict['some_key'] = 'something'
    assert list(redisdict.keys()) == ['some_key']

    another_key = 'another_key'
    redisdict[another_key] = 'something 2'
    assert sorted(list(redisdict.keys())) == [another_key, 'some_key']

    del redisdict['some_key']
    assert list(redisdict.keys()) == [another_key]


def test_clear(redisdict):
    some_key = str(uuid.uuid4())
    redisdict[some_key] = {'a': 'b'}

    redisdict.clear()

    assert list(redisdict.keys()) == []

    with pytest.raises(KeyError):
        redisdict[some_key]

    with pytest.raises(KeyError):
        redisdict[some_key]['a']


def test_has_key(redisdict):
    some_key = str(uuid.uuid4())
    redisdict[some_key] = 'something'

    assert redisdict.has_key(some_key) is True  # noqa
    assert redisdict.has_key('unknown') is False  # noqa


def test_contains(redisdict):
    some_key = str(uuid.uuid4())
    redisdict[some_key] = 'something'

    assert (some_key in redisdict) is True
    assert ('unknown' in redisdict) is False


def test_cache_in_sync_when_update_operations_performed(redisdict):
    redisdict[1] = {'stuff': {}}
    assert redisdict.cache == redisdict
    assert redisdict == {1: {'stuff': {}}}
    assert redisdict.cache == redisdict

    redisdict[1]['stuff'] = {'a': 'b'}
    assert redisdict.cache == redisdict

    assert redisdict.cache == {1: {'stuff': {'a': 'b'}}}
    assert redisdict == {1: {'stuff': {'a': 'b'}}}
    assert redisdict[1]['stuff'] == {'a': 'b'}
    assert redisdict[1] == {'stuff': {'a': 'b'}}
    assert redisdict.cache == redisdict


def test_dict_operations(redisdict, redis, key):
    # exercise setitem
    redisdict['10'] = 'ten'
    redisdict['20'] = 'twenty'
    redisdict['30'] = 'thirty'
    assert RedisDict(persistence=redis, key=key) == redisdict

    # exercise delitem
    del redisdict['20']
    assert RedisDict(persistence=redis, key=key) == redisdict

    # check getitem and setitem
    assert redisdict['10'] == 'ten'
    assert RedisDict(persistence=redis, key=key) == redisdict

    # check keys() and delitem
    assert sorted(list(redisdict.keys())) == sorted(['10', '30'])
    assert RedisDict(persistence=redis, key=key) == redisdict

    # has_key
    assert redisdict.has_key('10')  # noqa
    assert not redisdict.has_key('20')  # noqa

    # __contains__
    assert '10' in redisdict
    assert '20' not in redisdict

    # __iter__
    assert sorted([k for k in redisdict]) == ['10', '30']

    # __len__
    assert len(redisdict) == 2

    # items
    assert sorted(list(redisdict.items())) == [('10', 'ten'), ('30', 'thirty')]

    # keys
    assert sorted(list(redisdict.keys())) == ['10', '30']

    # values
    assert sorted(list(redisdict.values())) == ['ten', 'thirty']

    # get
    assert redisdict.get('10') == 'ten'
    assert redisdict.get('15', 'fifteen') == 'fifteen'
    assert redisdict.get('15') is None

    # setdefault
    assert redisdict.setdefault('40', 'forty') == 'forty'
    assert redisdict.setdefault('10', 'null') == 'ten'
    del redisdict['40']
    assert RedisDict(persistence=redis, key=key) == redisdict

    # pop
    assert redisdict.pop('10') == 'ten'
    assert 10 not in redisdict
    redisdict['10'] = 'ten'
    assert redisdict.pop('x', 1) == 1
    redisdict['x'] = 42
    assert redisdict.pop('x', 1) == 42
    assert RedisDict(persistence=redis, key=key) == redisdict

    # popitem
    k, v = redisdict.popitem()
    assert k not in redisdict
    redisdict[k] = v

    # clear
    redisdict.clear()
    assert len(redisdict) == 0

    # empty popitem
    with pytest.raises(KeyError):
        redisdict.popitem()

    # update
    redisdict.update({'10': 'ten', '20': 'twenty'})
    assert redisdict['10'] == 'ten'
    assert redisdict['20'] == 'twenty'

    # cmp
    normal_dict = {'10': 'ten', '20': 'twenty'}
    assert normal_dict == {'10': 'ten', '20': 'twenty'}
    redis.flushall()
    redisdict2 = RedisDict(persistence=redis, key=key)
    redisdict2['20'] = 'twenty'
    redisdict2['10'] = 'ten'
    assert normal_dict == redisdict2

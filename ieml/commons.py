import functools
import glob
import logging
import os
import pickle
from collections import OrderedDict
from enum import Enum
from itertools import chain
from sys import stderr
from typing import List
import hashlib
from time import time

from ieml import logger


class cached_property:
    def __init__(self, factory):
        self._factory = factory
        self._attr_name = factory.__name__

    def __get__(self, instance, owner):
        attr = self._factory(instance)
        setattr(instance, self._attr_name, attr)
        return attr

class LastUpdatedOrderedDict(OrderedDict):
    'Store items in the order the keys were last added'
    def __setitem__(self, key, value, **kwargs):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value, **kwargs)


class TreeStructure:
    def __init__(self, *args, **kwargs):
        self._str = None
        self._paths = None
        self.children = None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self._str

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if not isinstance(other, (TreeStructure, str)):
            return False

        return self._str == str(other)

    def __hash__(self):
        """Since the IEML string for any proposition AST is supposed to be unique, it can be used as a hash"""
        return self.__str__().__hash__()

    def __iter__(self):
        """Enables the syntactic sugar of iterating directly on an element without accessing "children" """
        return self.children.__iter__()

    def tree_iter(self):
        yield self
        for c in self.children:
            yield from c.tree_iter()


def fullname(cls):
    return cls.__module__ + '.' + cls.__qualname__


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            # this code is to clean up duplicate class if we reload modules
            to_remove = [i for i in cls._instances if fullname(i) == fullname(cls)]
            for i in to_remove:
                del cls._instances[i]

            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]


class FolderWatcherCache:
    def __init__(self, db_path: str, pattern: str, cache_folder: str, name: str):
        """
        Cache that check if `folder` content has changed. Compute a hash of the files in the folder and
        get pruned if the content of this folder change.

        :param folder: the folder to watch
        :param cache_folder: the folder to put the cache file
        """
        self.db_path = db_path
        self.pattern = pattern
        self.files = sorted([os.path.abspath(ff) for ff in glob.glob(os.path.join(self.db_path, self.pattern), recursive=True)])
        self.cache_folder = os.path.abspath(cache_folder)
        self.name = name

    def update(self, obj) -> None:
        """
        Update the cache content, remove old cache files from the cache directory.

        :param obj: the object to pickle in the cache
        :return: None
        """
        for c in self._cache_candidates():
            os.remove(c)

        with open(self.cache_file, 'wb') as fp:
            pickle.dump(obj, fp, protocol=4)

    def get(self) -> object:
        """
        Unpickle and return the object stored in the cache file.
        :return: the stored object
        """
        with open(self.cache_file, 'rb') as fp:
            return pickle.load(fp)

    def is_pruned(self) -> bool:
        """
        Return True if the watched folder content has changed.
        :return: if the folder content changed
        """
        names = [p for p in self._cache_candidates()]
        if len(names) != 1:
            return True

        return self.cache_file != names[0]

    @property
    def cache_file(self) -> str:
        """
        :return: The cache file absolute path
        """
        res = b""
        for file in self.files:
            with open(file, 'rb') as fp:
                res += file[len(self.db_path)+1:].encode('utf8') + b":" + fp.read()

        return os.path.join(self.cache_folder, ".{}-cache.{}".format(self.name, hashlib.md5(res).hexdigest()))

    def _cache_candidates(self) -> List[str]:
        """
        Return all the cache files from the cache folder (the pruned and the current one)
        :return: All the cache files from the cache folder
        """
        return [os.path.join(self.cache_folder, n) for n in os.listdir(self.cache_folder)
                if n.startswith('.{}-cache.'.format(self.name))]

def monitor_decorator(name):
    def decorator(f):
        def wrapper(*args, **kwargs):
            before = time()
            args_str = ", ".join(chain(map(lambda e: str(e)[:100], args), map(lambda e: "{}={}".format(e[0], str(e[1])[:100]), kwargs.items())))
            res = f(*args, **kwargs)
            print("({:.2f}) {}# ({})".format(time() - before, name, args_str), file=stderr)
            return res

        functools.wraps(wrapper)
        return wrapper

    return decorator


def cache_results_watch_files(path, name):
    def decorator(f):
        def wrapper(*args, **kwargs):
            use_cache = args[0].use_cache
            self = args[0]
            cache_folder = self.cache_folder
            db_path = self.folder

            if use_cache:
                cache = FolderWatcherCache(db_path, path, cache_folder=cache_folder, name=name)
                if not cache.is_pruned():
                    logger.info("read_{}.cache: Reading cache at {}".format(name, cache.cache_file))
                    try:
                        instance = cache.get()
                    except Exception as e:
                        # cache.prune()
                        # raise e
                        instance = None
                else:
                    logger.info("read_{}.cache: Pruned cache at {}".format(name, cache_folder))
                    instance = None

                if instance:
                    return instance

            instance = f(*args, **kwargs)

            if use_cache and cache_folder:
                cache = FolderWatcherCache(db_path, path, cache_folder=cache_folder, name=name)

                logger.info("read_{}.cache: Updating cache at {}".format(name, cache.cache_file))
                cache.update(instance)

            return instance

        functools.wraps(wrapper)

        return wrapper

    return decorator


class DecoratedComponent:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._literal = None

    def clear_literal(self):
        self._literal = None

    def set_literal(self, value):
        from ieml.usl.decoration.instance import literal_context

        literal_context().push(self)
        self._literal = value

    def get_literal(self):
        return self._literal

class OrderedEnum(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

import sqlite3
from typing import Optional,  Union, Any
from collections.abc import MutableMapping
from pathlib import Path
import pickle
import shutil
import os
import multiprocessing


class SQLiteLRUCache(MutableMapping):
    """SQLite3 LRU cache with optional TTL"""

    def __init__(
            self,
            maxsize: int,
            path: Optional[Union[Path, str]] = None,
            ttl: Optional[int] = None,
            clear_on_start=False,
    ):
        """

        maxsize
        getsizeof
        ttl: time to live in seconds
        """

        if not ((path is None) or isinstance(path, (str, Path))):

            raise TypeError("path must be str or None")

        if not ((ttl is None) or isinstance(ttl, int)):
            raise TypeError("ttl must be int or None")

        if not ((maxsize is None) or isinstance(maxsize, int)):
            raise TypeError("maxsize must be int or None")

        # Absolute path to the cache
        path = Path(path).absolute() if path else Path(".") / ".cache"

        self.path = path
        self.ttl: Optional[int] = ttl
        self.maxsize = maxsize
        self.clear_on_start = clear_on_start

        # Though this is little heavy compared to threading's lock, but this helps this cache from
        # remaining agnostic of where it is being used (under thread / process context).
        # The lock is to avoid race conditions while accessing the sqlite cache database.
        self.lock = multiprocessing.Lock()
        self.db_name = "botocache.db"

        if clear_on_start:
            # Clear the cache
            shutil.rmtree(self.path)

        self.cache_db_path = os.path.join(str(self.path), self.db_name)

        # Delete any existing expired entries
        self.__delete_expired_entries()

    @staticmethod
    def create_cache_table(cursor):
        cursor.execute(
            """
        create table if not exists cache(
            key text primary key,
            value blob,
            created_at datetime not null default (strftime('%Y-%m-%d %H:%M:%f', 'NOW')),
            last_accessed_at datetime not null default (strftime('%Y-%m-%d %H:%M:%f', 'NOW'))


        );
        """
        )

    def __enter__(self):
        self.lock.acquire()
        # Creates the cache directory if it does not exist.
        self.path.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.cache_db_path)
        cursor = self.con.cursor()
        # Creates a cache table if it does not exists.
        self.create_cache_table(cursor=cursor)
        return cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.con.commit()
        # Close is necessary after every transaction as the same cache may be used by other programs.
        self.con.close()
        self.lock.release()

    def __getitem__(self, key):
        self.__delete_expired_entries()

        entry = None
        with self as cursor:
            entry = cursor.execute(
                "select value from cache where key = ?", (key,)
            ).fetchone()

        if entry is None:
            return self.__missing__(key)

        value = entry[0]

        value = pickle.loads(value)
        self.__update_last_accessed_at(key)
        return value

    def __missing__(self, key):
        raise KeyError(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        self.__delete_expired_entries()
        value_size = 1

        current_size = len(self)

        if value_size > self.maxsize:
            raise ValueError("value too large")

        while current_size + value_size > self.maxsize:
            self.popitem()

        with self as cursor:
                cursor.execute(
                    "insert or replace into cache(key, value) VALUES (?, ?)",
                    (key, pickle.dumps(value)),
                )

    def __delitem__(self, key):
        with self as cursor:
            cursor.execute("delete from cache where key = ?", (key,))

    def __contains__(self, key) -> bool:
        self.__delete_expired_entries()
        sql = "select true from cache where key = ?"
        maybe_row = None

        with self as cursor:
            maybe_row = cursor.execute(sql, (key,)).fetchone()

        if maybe_row is None:
            return False

        return True

    def __len__(self):
        self.__delete_expired_entries()
        sql = "select count(key) as length from cache;"
        with self as cursor:
            row = cursor.execute(sql).fetchone()
        return row[0]

    def __iter__(self):
        self.__delete_expired_entries()
        sql = "select key from cache;"
        with self as cursor:
            for (key,) in cursor.execute(sql):
                yield key

    def items(self):
        self.__delete_expired_entries()
        for key in self.__iter__():
            try:
                value = self[key]
                yield key, value
            except KeyError:
                continue

    def popitem(self):
        """Remove and return the `(key, value)` pair least recently used."""

        sql = "select key from cache order by last_accessed_at asc limit 1"

        maybe_row = None
        with self as cursor:
            maybe_row = cursor.execute(sql).fetchone()

        if maybe_row is None:
            msg = "%s is empty" % self.__class__.__name__
            raise KeyError(msg) from None

        key = maybe_row[0]

        return (key, self.pop(key))

    def __update_last_accessed_at(self, key):
        """Update the last accessed date for a key to now"""
        sql = """
        update
            cache
        set
            last_accessed_at = current_timestamp
        where
            key = ?
        """
        with self as cursor:
            cursor.execute(sql, (key,))

    def __delete_expired_entries(self):
        """Delete entries with an expired ttl"""
        if self.ttl is None:
            return

        sql = """
        delete from cache
        where
            (
                cast(strftime('%s', current_timestamp) as integer) -
                cast(strftime('%s', last_accessed_at) as integer)
            ) > ?
        """
        with self as cursor:
            cursor.execute(sql, (self.ttl,))
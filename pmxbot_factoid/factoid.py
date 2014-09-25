# -*- coding: utf-8 -*-
from __future__ import absolute_import

import re
import random
import six

import pmxbot
from pmxbot.core import regexp, command
from pmxbot.core import ContainsHandler
from pmxbot import storage

class RegexpFindHandler(ContainsHandler):
    class_priority = 4
    def __init__(self, *args, **kwargs):
        super(RegexpFindHandler, self).__init__(*args, **kwargs)
        if isinstance(self.pattern, six.string_types):
            self.pattern = re.compile(self.pattern, re.IGNORECASE)

    def match(self, message, channel):
        return self.pattern.findall(message)

    def process(self, message):
        return self.pattern.findall(message)

class Factoid(storage.SelectableStorage):

    @classmethod
    def initialize(cls):
        cls.store = cls.from_URI(pmxbot.config.database)
        cls._finalizers.append(cls.finalize)

    @classmethod
    def finalize(cls):
        del cls.store

class SQLiteFactoid(Factoid, storage.SQLiteStorage):
    def init_tables(self):
        query = "CREATE TABLE IF NOT EXISTS factoids (channel varchar, key varchar, factoid varchar, PRIMARY KEY (key));"
        self.db.execute(query)
        query = "CREATE INDEX IF NOT EXISTS factoid_lookup ON factoids (channel, key);"
        self.db.execute(query)
        self.db.commit()

    def get_factoid(self, channel, key):
        query = "SELECT factoid FROM factoids WHERE channel = ? AND key = ?"
        result = self.db.execute(query, [channel, key]).fetchall()
        if len(result) > 0:
            return result[0][0]
        else:
            return None

    def set_factoid(self, channel, key, factoid):
        query = "INSERT INTO factoids (channel, key, factoid) values (?, ?, ?)"
        try:
           self.db.execute(query, [channel, key, factoid])
           self.db.commit()
        except self.db.IntegrityError:
            currFactoid = self.get_factoid(channel, key)
            return (False, currFactoid)
        return (True, True)

    def update_factoid(self, channel, key, factoid):
        query = "INSERT OR REPLACE INTO factoids (channel, key, factoid) values (?, ?, ?)"
        try:
           self.db.execute(query, [channel, key, factoid])
           self.db.commit()
        except self.db.IntegrityError:
            return False
        return True

    def delete_factoid(self, channel, key):
        query = "DELETE FROM factoids WHERE channel = ? AND key = ?"
        try:
           self.db.execute(query, [channel, key])
           self.db.commit()
        except self.db.IntegrityError:
            factoid = self.get_factoid(key)
            return False
        return True


def regexpfind(name, regexp, doc=None, **kwargs):
    return RegexpFindHandler(
            name=name,
            doc=doc,
            pattern=regexp,
            **kwargs
    ).decorate


@regexpfind("createFactoid", r"^([^What|Where].+?) is (.*)")
def createFactoid(client, event, channel, nick, match):
    key = match[0][0].strip()
    factoid = match[0][1].strip()
    result, currFactoid = Factoid.store.set_factoid(channel, key, factoid)
    if not result:
        yield ("But %s is already %s" % (key, currFactoid))


@regexpfind("replaceFactoid", r"^no, (.+?) is (.*)")
def replaceFactoid(client, event, channel, nick, match):
    key = match[0][0].strip()
    factoid = match[0][1].strip()
    result = Factoid.store.update_factoid(channel, key, factoid)
    if result:
        yield "Got it!"
    else:
        yield "I failed to replace that factoid for some reason... Sorry..."


@regexp("getFactoid", r"^(?:What is|Where is) (.*[^?])?")
def getFactoid(client, event, channel, nick, match):
    key = match.group(1)
    flavors = ['I think that', 'Perhaps', 'Maybe', 'Possibly',
               'Someone told me that', 'I heard that', 'A wise man once said',
               'I read somewhere that', 'I could be wrong but',
               'The magic 8 ball says that']
    factoid = Factoid.store.get_factoid(channel, key)
    if factoid is not None:
        yield ("%s %s is %s" % (random.choice(flavors), key, factoid))

@regexp("delFactoid", r"^forget (.*)")
def delFactoid(client, event, channel, nick, match):
    key = match.group(1)
    factoid = Factoid.store.delete_factoid(channel, key)
    if factoid:
        yield ("Like it was never there...")

@command(aliases='f')
def factoid(client, event, channel, nick, rest):
    """
    You can teach me a factoid by saying "X is Y",
     You can get a factoid by asking "What is X?",
     You can replace an existing factoid by saying "no, X is Y",
     and you can delete a factoid by saying "Forget X".
    """
    pass


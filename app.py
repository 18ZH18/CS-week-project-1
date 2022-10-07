#!/usr/bin/env python3
from aiohttp import web
from os import mkdir
from datetime import datetime
from pathlib import Path
import logging
import sys
import sqlite3

"""
Logging Stuff
"""

try:
    mkdir(".logs")
except FileExistsError:
    pass

fp = f'./.logs/{datetime.now()}.log'.replace(' ', '-')

if sys.platform.lower() == 'win32':
    fp = fp.replace(':', '.')


logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # we don't want to filter messages yet

fh = logging.FileHandler(fp)
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO) # we don't want to clog up the console

fmt = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] : %(message)s')

ch.setFormatter(fmt)
fh.setFormatter(fmt)

logger.addHandler(ch)
logger.addHandler(fh)

"""
Database Stuff
"""
class DatabaseHandler():
    """
    A simple database wrapper that
    manages an sqlite database
    """

    def __init__(self, db_path):
        self.connection = sqlite3.connect(db_path)
        cursor = self.get_cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                           userid INTEGER PRIMARY KEY,
                           name TEXT NOT NULL UNIQUE
                       );""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS guesses(
                            guessid    INTEGER PRIMARY KEY,
                            guesser    INTEGER NOT NULL,
                            numguesses INTEGER NOT NULL,
                            finished   BOOLEAN NOT NULL,
                            FOREIGN KEY (guesser) REFERENCES users(id)
                       );""")
        self.commit()

    def __del__(self):
        self.commit()
        self.connection.close()

    def get_cursor(self):
        return self.connection.cursor()

    def commit(self):
        return self.connection.commit()


    def has_user(self, username):
        cur = self.get_cursor()
        res = cur.execute("SELECT 1 FROM users WHERE name=?;", (username,))
        return bool(res.fetchall())
    
    def get_user_id(username):
        cur = self.get_cursor()
        res = cur.execute("SELECT userid FROM users WHERE name=?;", (username,))
        return res.fetchall()[0]

    def add_user(self, username):
        if self.has_user(username):
            return False
        cur = self.get_cursor()
        cur.execute("INSERT INTO users(name) VALUES (?);", (username,))
        self.commit()
        return True

    def add_guess(self, userid, numguesses, finished):
        cur = self.get_cursor()
        cur.execute(
            "INSERT INTO guesses(guesser, numguesses, finished) VALUES (?, ?, ?);",
            (userid, numguesses, finished)
        )
        self.commit()





"""
AIOHTTP Stuff
"""

routes = web.RouteTableDef()

@routes.post('/api/users')
async def add_user(request):
    db = request.app["database"]
    json = await request.json()
    username = json["name"]
    if db.add_user(username):
        return web.HTTPCreated()
    else:
        return web.HTTPConflict()

@routes.post('/api/guesses')
async def add_guess(request):
    db = request.app["database"]
    json = await request.json()
    if "name" in json:
        user_id = db.get_user_id(json["name"])
    elif "userid" in json:
        user_id = json["userid"]
    else:
        return web.HTTPBadRequest()
    db.add_guess(userid, json["guess"], json["correct"])
    return web.HTTPCreated()



    
@web.middleware
async def static_server(request, handler):

    rel_fp = Path(request.path).relative_to('/')
    fp = Path('./static') / rel_fp

    if fp.is_dir(): # somebody is looking for /
        fp /= 'index.html'

    if not fp.exists():
        return await handler(request)

    return web.FileResponse(fp)

if __name__ == '__main__':
    app = web.Application(middlewares=[static_server])
    app["database"] = DatabaseHandler("./database.db")
    app.add_routes(routes)
    web.run_app(app, port=8000)





"""Small database helper for the local LDM databases (no psql on this machine).

  python docs/ldm/tools/pgdb.py list
  python docs/ldm/tools/pgdb.py copy <source> <target>   (drops <target> first; copies the filestore too)
  python docs/ldm/tools/pgdb.py drop <name>

Reads the connection from odoo19_ldm.conf. Only databases whose name starts
with ldm_ are touched.
"""
import configparser
import os
import shutil
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
conf = configparser.ConfigParser()
conf.read(os.path.join(ROOT, "odoo19_ldm.conf"))
opts = conf["options"]
DATA = os.path.join(ROOT, opts.get("data_dir", ".odoo_data_ldm"))


def connect():
    cn = psycopg2.connect(host=opts.get("db_host", "localhost"), port=opts.get("db_port", "5432"),
                          user=opts["db_user"], password=opts["db_password"], dbname="postgres")
    cn.autocommit = True
    return cn


def guard(name):
    if not name.startswith("ldm_"):
        sys.exit(f"refusing to touch {name}: not an ldm_ database")


def drop(cur, name):
    guard(name)
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,))
    cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
    shutil.rmtree(os.path.join(DATA, "filestore", name), ignore_errors=True)


def main():
    command = sys.argv[1]
    cur = connect().cursor()
    if command == "list":
        cur.execute("SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database "
                    "WHERE datname LIKE 'ldm_%%' ORDER BY 1")
        for name, size in cur.fetchall():
            print(name, size)
    elif command == "drop":
        drop(cur, sys.argv[2])
        print("dropped", sys.argv[2])
    elif command == "copy":
        source, target = sys.argv[2], sys.argv[3]
        guard(source)
        drop(cur, target)
        cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (source,))
        cur.execute(f'CREATE DATABASE "{target}" WITH TEMPLATE "{source}" OWNER "{opts["db_user"]}"')
        src_store = os.path.join(DATA, "filestore", source)
        if os.path.isdir(src_store):
            shutil.copytree(src_store, os.path.join(DATA, "filestore", target))
        print("copied", source, "->", target)


if __name__ == "__main__":
    main()

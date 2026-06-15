import os
import socket

import psycopg
from flask import Flask, Response


app = Flask(__name__)


def db_conninfo() -> str:
    return (
        f"host={os.environ.get('DB_HOST', 'db')} "
        f"user={os.environ.get('DB_USER', 'postgres')} "
        f"password={os.environ.get('DB_PASSWORD', '')} "
        f"dbname={os.environ.get('DB_NAME', 'postgres')} "
        "connect_timeout=2"
    )


def check_db() -> tuple[bool, str]:
    try:
        with psycopg.connect(db_conninfo()) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
                cur.fetchone()
        return True, "ok"
    except Exception as exc:
        app.logger.warning("db unreachable: %s", exc)
        return False, str(exc)


@app.get("/")
def index():
    ok, _ = check_db()
    status = "db=ok" if ok else "db=down"
    return f"Hello from {socket.gethostname()} | {status}\n"


@app.get("/healthz")
def healthz():
    ok, message = check_db()
    if ok:
        return "ok\n"
    return Response(f"db unreachable: {message}\n", status=503)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

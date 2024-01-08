import os
import psycopg2
from retry import retry
from psycopg2.extras import DictCursor

conn = None

@retry(delay=5, tries=6)
def get_conn():
    conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USERNAME'],
            password=os.environ['DB_PASSWORD'],
            port= os.environ['DB_PORT'],
            cursor_factory=DictCursor
            )
    return conn

def close_conn():
    if conn is not None:
        conn.close()
        conn = None

def run_sql(cursor, query: str, parameters: tuple = None, fetch=True):
    cursor.execute(query, parameters) if parameters else cursor.execute(query)

    result = None
    if fetch:
        try:
            result = cursor.fetchall()
        except psycopg2.ProgrammingError:
            pass

    cursor.close()
    return result

import os

from tdda.constraints.db.drivers import (
    get_db_handler,
)

def main(table, sql_path, conn=None, dbtype=None):
    h = get_db_handler(table, dbtype=dbtype, conn=conn)
    dbc = h.dbc

    print(str(h.db))
    print(str(dbc))
    print(str(h))
    with open(sql_path) as f:
        s = f.read()
        queries = [q.strip() for q in s.split(';\n')]
        queries = [q for q in queries if q]
        h.execute_commit(queries)


connection_file = os.path.expanduser('~/.tdda_db_conn_docker_postgres')
pg_sql_path = 'init/postgres-create-elements.sql'
main('e', pg_sql_path, conn=connection_file, )

mysql_sql_path = 'init/mysql-create-elements.sql'
main('mysql:e', mysql_sql_path)

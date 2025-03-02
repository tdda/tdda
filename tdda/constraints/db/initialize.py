import os

from tdda.constraints.db.drivers import (
    database_connection,
    SQLDatabaseHandler,
    parse_table_name,
)

def get_db_connector(table, dbtype=None, **kw):
    """
    Returns a connection for the database table specified.

    Args:

        table: tablename
               or dbtype:tablename

        dbtype: dbtype if not in table

        keyword args: Override parameters
                      Parameters are read from the connection file
                      (.tdda_db_conn_dbtype), but can be overridden her.

    Returns: A DBConnector, with a .connection attribute
             and other attributes for the connection properties.
    """
    (table, dbtype) = parse_table_name(table, dbtype)
    return database_connection(table=table, dbtype=dbtype, **kw)


def get_db_handler(table, dbtype=None, **kw):
    """
    Returns a handler for the database table specified.

    Args:

        table: tablename
               or dbtype:tablename

        dbtype: dbtype if not in table

        keyword args: Override parameters
                      Parameters are read from the connection file
                      (.tdda_db_conn_dbtype), but can be overridden her.

    Returns: A SQLDBHandler, with
                .db      containing for the database connector
                .dbc     containing for the database connection
                .cursor  containing the cursor
             and methods for executing queries.
    """
    (table, dbtype) = parse_table_name(table, dbtype)
    db = database_connection(table=table, dbtype=dbtype, **kw)
    return SQLDatabaseHandler(dbtype, db)


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


# connection_file = os.path.expanduser('~/.tdda_db_conn_docker_postgres')
# pg_sql_path = 'init/postgres-create-elements.sql'
# main('e', pg_sql_path, conn=connection_file, )

mysql_sql_path = 'init/mysql-create-elements.sql'
main('mysql:e', mysql_sql_path)

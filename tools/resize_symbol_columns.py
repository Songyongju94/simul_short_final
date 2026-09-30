"""Resize symbol columns in explicitly selected databases; no application/config imports.

Preview: python tools/resize_symbol_columns.py --database db_sd17 --user root
Apply:   python tools/resize_symbol_columns.py --database db_sd17 --user root --apply
Repeat --database to select additional databases. Stop table writers before applying.
The password is requested interactively and is never printed or stored.
"""
import argparse
from getpass import getpass


def identifier(value):
    return '`' + value.replace('`', '``') + '`'


def plan_changes(connection, databases):
    plans = []
    with connection.cursor() as cursor:
        for database in dict.fromkeys(databases):
            # Also verifies access to the explicitly selected database.
            cursor.execute('USE ' + identifier(database))
            cursor.execute("""
                SELECT c.* FROM information_schema.COLUMNS c
                JOIN information_schema.TABLES t
                  ON t.TABLE_SCHEMA=c.TABLE_SCHEMA AND t.TABLE_NAME=c.TABLE_NAME
                WHERE c.TABLE_SCHEMA=%s AND LOWER(c.COLUMN_NAME)='symbol'
                  AND t.TABLE_TYPE='BASE TABLE'
                ORDER BY c.TABLE_NAME
            """, (database,))
            columns = cursor.fetchall()
            for column in columns:
                if column['DATA_TYPE'].lower() not in ('varchar', 'char') or column['EXTRA']:
                    raise ValueError('Unsupported symbol column: ' + database + '.' + column['TABLE_NAME'])
                if int(column['CHARACTER_MAXIMUM_LENGTH']) == 32:
                    continue
                table = identifier(database) + '.' + identifier(column['TABLE_NAME'])
                name = identifier(column['COLUMN_NAME'])
                if int(column['CHARACTER_MAXIMUM_LENGTH']) > 32:
                    cursor.execute('SELECT 1 FROM ' + table + ' WHERE CHAR_LENGTH(' + name + ') > 32 LIMIT 1')
                    if cursor.fetchone() is not None:
                        raise ValueError('Values longer than 32 exist in ' + table + '; no schema changes applied')
                definition = column['DATA_TYPE'].upper() + '(32)'
                definition += ' CHARACTER SET ' + identifier(column['CHARACTER_SET_NAME'])
                definition += ' COLLATE ' + identifier(column['COLLATION_NAME'])
                definition += ' NULL' if column['IS_NULLABLE'] == 'YES' else ' NOT NULL'
                if column['COLUMN_DEFAULT'] is not None:
                    definition += ' DEFAULT ' + connection.escape(column['COLUMN_DEFAULT'])
                elif column['IS_NULLABLE'] == 'YES':
                    definition += ' DEFAULT NULL'
                definition += ' COMMENT ' + connection.escape(column['COLUMN_COMMENT'])
                plans.append('ALTER TABLE ' + table + ' MODIFY COLUMN ' + name + ' ' + definition)
    return plans


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=3306)
    parser.add_argument('--user', required=True)
    parser.add_argument('--database', action='append', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    import pymysql
    connection = pymysql.connect(host=args.host, port=args.port, user=args.user,
                                 password=getpass('MySQL password: '), charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor, autocommit=True)
    try:
        # Reject invalid/narrowing data across all selected tables before any ALTER.
        plans = plan_changes(connection, args.database)
        for sql in plans:
            print(sql + ';')
        if not args.apply:
            print('Preview only. Re-run with --apply to modify the selected databases.')
            return
        # MySQL DDL commits independently; successful earlier ALTERs cannot roll back.
        # Re-running is safe: columns already sized 32 are skipped.
        with connection.cursor() as cursor:
            for sql in plans:
                cursor.execute(sql)
                print('Applied.')
        print('Completed: ' + str(len(plans)) + ' columns changed.')
    finally:
        connection.close()


if __name__ == '__main__':
    main()

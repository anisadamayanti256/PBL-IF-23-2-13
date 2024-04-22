from mysql.connector import connect

class DatabaseOperations:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def __enter__(self):
        self.connection = connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection.is_connected():
            self.connection.commit()
            self.cursor.close()
            self.connection.close()

    def delete_record(self, table, condition):
        query = f"DELETE FROM {table} WHERE {condition[0]}=%s"
        self.cursor.execute(query, (condition[1],))

    def close_cursor(self):
        self.cursor.close()

    def __del__(self):
        if hasattr(self, 'connection') and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()

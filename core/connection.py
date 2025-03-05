from . import settings
import psycopg
import logging

class Connection:
    def __init__(self):
        self.conn = psycopg.connect( 
                host=settings.settings.DATABASE_HOST,
                dbname=settings.settings.DATABASE_NAME,
                user=settings.settings.DATABASE_USER,
                password=settings.settings.DATABASE_PASSWORD,
                port=settings.settings.DATABASE_PORT
            )
        logging.info("Connection established")

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info("Connection closed")

    def get_connection(self):
        return self.conn

    def create_table_if_not_exists(self, table_name):
        try:
            cur = self.conn.cursor()
            # Use string formatting for table name since psycopg doesn't support parameterized DDL
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id serial PRIMARY KEY,
                    filename text UNIQUE NOT NULL,
                    source_url text,
                    file_data bytea,
                    created_at timestamp DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
            logging.info(f"Table {table_name} created or already exists")
        except Exception as e:
            logging.error(f"Error creating table in database: {e}")
            raise e

    def check_table_exists(self, table_name):
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (table_name,))
            return cur.fetchone()[0]
        except Exception as e:
            logging.error(f"Error checking table existence: {e}")
            return False

    def save_to_db(self, filename, table_name, source_url=None):
        try:
            if not self.check_table_exists(table_name):
                self.create_table_if_not_exists(table_name)
            
            cur = self.conn.cursor()
            cur.execute(f"""
                INSERT INTO {table_name} (filename, source_url) 
                VALUES (%s, %s) 
                ON CONFLICT (filename) DO NOTHING
            """, (filename, source_url))
            self.conn.commit()
            logging.info(f"File {filename} saved to database")
        except Exception as e:
            logging.error(f"Error saving file to database: {e}")
            raise e

    def get_files(self, table_name):
        try:
            cur = self.conn.cursor()
            cur.execute(f"SELECT filename, source_url, created_at FROM {table_name} ORDER BY created_at DESC")
            return cur.fetchall()
        except Exception as e:
            logging.error(f"Error getting files from database: {e}")
            return []

    def is_file_in_db(self, filename, table_name) -> bool:
        try:
            if not self.check_table_exists(table_name):
                return False
            
            cur = self.conn.cursor()
            cur.execute(f"SELECT EXISTS (SELECT 1 FROM {table_name} WHERE filename = %s)", (filename,))
            return cur.fetchone()[0]
        except Exception as e:
            logging.error(f"Error checking existence of file in database: {e}")
            return False
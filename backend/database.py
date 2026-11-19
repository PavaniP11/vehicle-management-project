import mysql.connector
from flask import current_app

def get_connection():
    return mysql.connector.connect(**current_app.config["DB_CONFIG"])

def rows(cursor):
    return [dict(zip(cursor.column_names, row)) for row in cursor.fetchall()]

def row(cursor):
    result = cursor.fetchone()
    return dict(zip(cursor.column_names, result)) if result else None


from dash_app import app
import os
from load_data import create_tables_and_load_data

# This is what Gunicorn will use
app = app.server

if __name__ == '__main__':
    # Always try to create and populate the database
    try:
        create_tables_and_load_data()
        print("Database initialized and data loaded successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
    
    from dash_app import app as dash_app
    dash_app.run_server(host='0.0.0.0', port=5000, debug=True)

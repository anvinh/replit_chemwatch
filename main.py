
from dash_app import app

# This is what Gunicorn will use
app = app.server

if __name__ == '__main__':
    from dash_app import app as dash_app
    dash_app.run_server(host='0.0.0.0', port=5000, debug=True)

import os
from app import create_app

app_env = os.environ.get('FLASK_ENV', 'default')
app = create_app(app_env)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6002)

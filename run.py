from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Using a fixed port makes it easy for the test script to connect.
    # Using os.getenv allows for flexibility in deployment environments.
    port = int(os.getenv("PORT", 5009))
    app.run(debug=True, host='0.0.0.0', port=port)

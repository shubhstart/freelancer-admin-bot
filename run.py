from freelancer_admin import create_app
import os
import sys

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    if debug:
        print(f"Starting development server on http://127.0.0.1:{port}")
        app.run(debug=True, use_reloader=False, port=port)
    else:
        from waitress import serve
        print(f"Starting production server (Waitress) on port {port}...")
        serve(app, host='0.0.0.0', port=port)


from __future__ import annotations
import os
import sys

# Ensure src/ is on sys.path so the consolidated package can be imported
PROJECT_ROOT = os.path.dirname(__file__)
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from gemini_ird_pricer import create_app

# Keep this file as a small entrypoint to run the Flask app using the app factory
app = create_app()

if __name__ == '__main__':
    # Bind to all interfaces in container; allow PORT override
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', True))
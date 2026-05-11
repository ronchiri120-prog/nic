import os
from waitress import serve
from quicklender_project.wsgi import application

# Production WSGI server configuration
PORT = int(os.environ.get('PORT', 8000))
HOST = os.environ.get('HOST', '127.0.0.1')
THREADS = int(os.environ.get('THREADS', 8))
URL_PREFIX = os.environ.get('URL_PREFIX', '')

print(f"Starting Waitress production server on http://{HOST}:{PORT}")
print("Press Ctrl+C to stop the server")
print(f"Threads: {THREADS}")

serve(
    application,
    host=HOST,
    port=PORT,
    threads=THREADS,
    url_prefix=URL_PREFIX,
    # Security settings
    clear_untrusted_proxy_headers=True,
    trusted_proxy='*',
    trusted_proxy_headers='x-forwarded-for x-forwarded-host x-forwarded-proto',
    # Performance settings
    connection_limit=1000,
    backlog=2048,
    recv_bytes=65536,
    send_bytes=65536,
    # Logging
    ident='quicklender',
)

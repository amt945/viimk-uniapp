#!/usr/bin/env python3
"""Serve dist/build/h5 static files on port 8080, proxy /__pyapi/* to localhost:3001."""
import os
import sys
import requests
from flask import Flask, send_from_directory, Response, request, abort

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, 'dist', 'build', 'h5')
PYAPI = 'http://localhost:3001'
app = Flask(__name__, static_folder=None)

@app.route('/__pyapi/<path:sub>', methods=['GET','POST','PUT','DELETE','OPTIONS'])
def proxy(sub):
    url = f'{PYAPI}/{sub}'
    qs = request.query_string
    try:
        r = requests.request(
            method=request.method,
            url=url + ('?'+qs.decode() if qs else ''),
            data=request.get_data(),
            headers={k:v for k,v in request.headers if k.lower() not in ('host','content-length')},
            timeout=30,
            allow_redirects=True
        )
        excluded = ['content-encoding','content-length','transfer-encoding','connection']
        headers = [(k,v) for k,v in r.raw.headers.items() if k.lower() not in excluded]
        return Response(r.content, status=r.status_code, headers=headers)
    except Exception as e:
        return Response(f'proxy error: {e}', status=502)

@app.route('/', defaults={'p': ''})
@app.route('/<path:p>')
def static_or_index(p):
    target = os.path.join(STATIC_DIR, p) if p else STATIC_DIR
    if os.path.isfile(target):
        return send_from_directory(STATIC_DIR, p)
    # fallback to index.html
    return send_from_directory(STATIC_DIR, 'index.html')

if __name__ == '__main__':
    print(f'[proxy-static] serving {STATIC_DIR} on 0.0.0.0:8080, /__pyapi -> {PYAPI}')
    app.run(host='0.0.0.0', port=8080, threaded=False)

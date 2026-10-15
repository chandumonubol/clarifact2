"""Start mock server and test - different content type."""
import subprocess, sys, os, time, urllib.request, json

os.chdir('C:\\projects\\clarifact-media')

proc = subprocess.Popen(
    [sys.executable, 'scripts\\mock_server.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

time.sleep(3)

if proc.poll() is not None:
    stderr = proc.stderr.read().decode()
    print('SERVER CRASHED: ' + stderr)
    sys.exit(1)

results = []

try:
    # Test analyze WITHOUT explicit Content-Type (let requests library handle it)
    # Just send form data as bytes
    data = 'text=test+claim'.encode()
    
    # Method 1: urllib with just data
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:8001/analyze',
            data=data,
            method='POST'
        )
        resp = urllib.request.urlopen(req, timeout=5)
        result = json.loads(resp.read().decode())
        results.append('PASS Method1: ' + json.dumps(result, indent=2))
    except Exception as e:
        results.append('FAIL Method1: ' + str(e))
    
    # Method 2: with Content-Type
    try:
        req2 = urllib.request.Request(
            'http://127.0.0.1:8001/analyze',
            data=data,
            method='POST'
        )
        req2.add_header('Content-Type', 'application/x-www-form-urlencoded')
        resp2 = urllib.request.urlopen(req2, timeout=5)
        result2 = json.loads(resp2.read().decode())
        results.append('PASS Method2: ' + json.dumps(result2, indent=2))
    except Exception as e:
        results.append('FAIL Method2: ' + str(e))
    
finally:
    proc.terminate()
    proc.wait()
    results.append('Server stopped')

for r in results:
    print(r)
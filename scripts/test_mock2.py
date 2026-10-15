"""Full test: start mock server, test endpoints."""
import subprocess, time, urllib.request, json, sys, os

# Start mock server in background
proc = subprocess.Popen(
    [sys.executable, 'C:\\projects\\clarifact-media\\scripts\\mock_server.py'],
    cwd='C:\\projects\\clarifact-media',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Wait for startup
time.sleep(3)

output_lines = []

try:
    # Test health
    resp = urllib.request.urlopen('http://localhost:8001/health', timeout=5)
    output_lines.append('Health: ' + resp.read().decode())
    
    # Test analyze with POST text (form-encoded)
    req = urllib.request.Request(
        'http://localhost:8001/analyze', 
        data='text=test+claim'.encode(), 
        method='POST'
    )
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    resp = urllib.request.urlopen(req, timeout=5)
    result = json.loads(resp.read().decode())
    output_lines.append('Analyze text: ' + json.dumps(result, indent=2))
    
    job_id = result.get('job_id')
    if job_id:
        # Poll for results
        for i in range(15):
            time.sleep(1)
            resp = urllib.request.urlopen('http://localhost:8001/jobs/' + job_id, timeout=5)
            job = json.loads(resp.read().decode())
            status = job.get('status', '')
            step = job.get('step', '')
            output_lines.append('Poll ' + str(i) + ': Status=' + status + ', Step=' + step)
            if status == 'done':
                result_str = json.dumps(job.get('result'), indent=2)
                output_lines.append('Result: ' + result_str)
                break
            elif status == 'error':
                err = job.get('error')
                output_lines.append('Error: ' + str(err))
                break
    else:
        output_lines.append('No job_id returned')
finally:
    proc.terminate()
    proc.wait()
    output_lines.append('Server stopped')

# Print all results
for line in output_lines:
    print(line)
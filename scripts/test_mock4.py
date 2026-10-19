"""Start mock server and test it - all in one Python process."""
import subprocess, sys, os, time, urllib.request, json

# Change to the project directory
os.chdir('C:\\projects\\clarifact-media')

# Start mock server
proc = subprocess.Popen(
    [sys.executable, 'scripts\\mock_server.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Wait for startup
time.sleep(3)

# Check if server crashed
if proc.poll() is not None:
    stderr = proc.stderr.read().decode()
    print('SERVER CRASHED: ' + stderr)
    sys.exit(1)

results = []

try:
    # Test 1: Health
    try:
        resp = urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5)
        results.append('PASS Health: ' + resp.read().decode())
    except Exception as e:
        results.append('FAIL Health: ' + str(e))
    
    # Test 2: Analyze with text
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:8001/analyze',
            data='text=test+claim'.encode(),
            method='POST'
        )
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        resp = urllib.request.urlopen(req, timeout=5)
        result = json.loads(resp.read().decode())
        results.append('PASS Analyze text: job_id=' + result.get('job_id', 'MISSING'))
    except Exception as e:
        results.append('FAIL Analyze text: ' + str(e))
    
    # Test 3: Poll for job completion
    job_id = None
    # Try to get job_id from the analyze response
    # If it failed, try a second approach
    if 'job_id' in results[-1] if results else False:
        # Extract job_id
        import re
        m = re.search(r'job_id=(\w+)', results[-1])
        if m:
            job_id = m.group(1)
    
    if job_id:
        for i in range(20):
            time.sleep(1)
            try:
                resp = urllib.request.urlopen('http://127.0.0.1:8001/jobs/' + job_id, timeout=5)
                job = json.loads(resp.read().decode())
                status = job.get('status', '')
                step = job.get('step', '')
                results.append('Poll ' + str(i) + ': Status=' + status + ', Step=' + step)
                if status == 'done':
                    results.append('PASS Job done!')
                    results.append('Result: ' + json.dumps(job.get('result'), indent=2))
                    break
                elif status == 'error':
                    results.append('FAIL Job error: ' + str(job.get('error')))
                    break
            except Exception as e:
                results.append('FAIL Poll ' + str(i) + ': ' + str(e))
                break
    else:
        results.append('SKIP No job_id available')
        
finally:
    proc.terminate()
    proc.wait()
    results.append('Server stopped')

# Print results
for r in results:
    print(r)
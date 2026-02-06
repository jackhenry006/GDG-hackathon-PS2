import time, urllib.request, json

def call(u):
    start = time.time()
    try:
        r = urllib.request.urlopen(u, timeout=30).read().decode()
        dt = time.time() - start
        print(u, '->', len(r), 'bytes,', f'{dt:.2f}s')
        try:
            obj = json.loads(r)
            print(json.dumps(obj, indent=2)[:1000])
        except Exception:
            print(r[:1000])
    except Exception as e:
        print('ERROR', u, e)

queries = ['test', 'ayushman tripathy', 'long query to test latency and behavior']
for q in queries:
    call(f'http://127.0.0.1:8001/search?query={urllib.request.quote(q)}')

call('http://127.0.0.1:8001/notifications')

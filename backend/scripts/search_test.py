import urllib.request, json

url = 'http://127.0.0.1:8000/search?query=registration'
try:
    r = json.load(urllib.request.urlopen(url))
except Exception as e:
    print('ERROR', e)
    raise
print('results', len(r))
for i, it in enumerate(r[:5]):
    print(f"{i+1}. title={it.get('title')} source={it.get('source')} url={it.get('url')} id={it.get('doc_id')}")
    print(it.get('clean','')[:160])
    print()

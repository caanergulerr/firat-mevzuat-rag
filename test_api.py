import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:8000/query',
    data=json.dumps({"question": "Mazeret sınavı hakkı ne zaman kullanılabilir?"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        with open('test_result.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
except Exception as e:
    print("Error:", e)

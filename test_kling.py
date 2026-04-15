import urllib.request, json
req = urllib.request.Request('https://api.klingai.com/v1/videos/image2video', method='POST')
req.add_header('Content-Type', 'application/json')
data = json.dumps({'image': '123', 'prompt': 'test'}).encode('utf-8')
try:
  urllib.request.urlopen(req, data=data)
except urllib.error.HTTPError as e:
  print('HTTP Error', e.code)
  print(e.read().decode())

path = '/home/parallels/test_pic.jpg'
import os

# Take picture
myCmd = 'fswebcam -D 3 -q -r 3264x2448 --rotate 90 --no-banner test_pic.jpg'
os.system(myCmd)

from google.cloud import vision

import io
client = vision.ImageAnnotatorClient.from_service_account_json('/home/parallels/creds.json')

with io.open(path, 'rb') as image_file:
    content = image_file.read()

image = vision.types.Image(content=content)

response = client.document_text_detection(image=image)

document = response.full_text_annotation
print(document.text)
from pyzbar.pyzbar import decode
from PIL import Image

def decode_qr(file_path):
    img = Image.open(file_path)
    decoded_objects = decode(img)
    if decoded_objects:
        return decoded_objects[0].data.decode("utf-8")
    return None

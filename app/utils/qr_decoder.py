import cv2
import qrcode

def decode_qr(file_path):
    img = cv2.imread(file_path)
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(img)
    if data:
        return data
    return None

def generate_qr_code(data, filename):
    img = qrcode.make(data)
    img.save(filename)
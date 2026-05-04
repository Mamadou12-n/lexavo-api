import qrcode, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Mode LAN — phone et PC doivent être sur le même Wi-Fi
URL = "exp://192.168.1.9:8082"

qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
    box_size=14,
    border=4,
)
qr.add_data(URL)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
img.save(r"C:\Users\bahma\Downloads\base-juridique-app\lexavo-qrcode.png")
print("URL Expo Go (LAN):", URL)
print("PNG genere:", "lexavo-qrcode.png")

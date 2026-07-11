import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

print("Bağlanılıyor...")
cred = credentials.Certificate("../firebase-key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://rival-clicker-default-rtdb.europe-west1.firebasedatabase.app/'
})

print("Tüm veriler temizleniyor (Eski yapı ve yeni yapı dahil)...")
db.reference('/').delete()
print("Sistem tertemiz sıfırlandı!")

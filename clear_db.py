"""Explicitly confirmed maintenance helper for clearing the configured database."""

import os

import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())

database_url = os.getenv("DATABASE_URL", "").strip()
credential_path = os.getenv("FIREBASE_KEY_PATH", "").strip()
confirmation = os.getenv("RIVAL_CONFIRM_DATABASE_CLEAR", "")

if confirmation != "DELETE-RIVAL-DATABASE":
    raise RuntimeError("Veritabanı temizleme onayı verilmedi.")
if not database_url or not credential_path or not os.path.isfile(credential_path):
    raise RuntimeError("DATABASE_URL veya FIREBASE_KEY_PATH güvenli biçimde ayarlanmamış.")

firebase_admin.initialize_app(
    credentials.Certificate(credential_path),
    {"databaseURL": database_url},
)
db.reference("/").delete()
print("Yapılandırılmış RIVAL veritabanı temizlendi.")

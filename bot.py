import discord
import os
from discord.ext import commands
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
from keep_alive import keep_alive

# .env dosyasını yükle
load_dotenv(find_dotenv())

print("Bot başlatılıyor, lütfen bekleyin...")


# Firebase Kurulumu
firebase_key_path = os.getenv("FIREBASE_KEY_PATH")
firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials_json:
    # Railway'de JSON string olarak env'den yükle
    import json
    cred_dict = json.loads(firebase_credentials_json)
    cred = credentials.Certificate(cred_dict)
elif firebase_key_path and os.path.exists(firebase_key_path):
    # Lokal'de dosyadan yükle
    cred = credentials.Certificate(firebase_key_path)
else:
    cred = credentials.Certificate("../firebase-key.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv("DATABASE_URL", "https://rival-clicker-default-rtdb.europe-west1.firebasedatabase.app/")
})



intents = discord.Intents.default()
intents.message_content = True
activity = discord.Game(name="Rival Clicker")
bot = commands.Bot(command_prefix='!', intents=intents, activity=activity, status=discord.Status.dnd)

@bot.event
async def on_ready():
    print('-----------------------------------------', flush=True)
    print(f'> Discord botu DND modunda aktif: {bot.user}', flush=True)
    print('> Firebase bulut baglantisi basarili!', flush=True)
    try:
        synced = await bot.tree.sync()
        print(f'> Slash komutlari senkronize edildi ({len(synced)} komut).', flush=True)
    except Exception as e:
        print(f'> Slash komutlari senkronize edilirken hata olustu: {e}', flush=True)
    print('-----------------------------------------', flush=True)

import random
import string
from discord import app_commands

@bot.tree.command(name="key", description="Yeni bir lisans anahtarı oluşturur.")
@app_commands.describe(
    sure="Lisans süresi: Gün sayısını yazın (Örn: 30) veya 'sinirsiz' yazın.",
    adet="Kaç adet anahtar üretileceği (Varsayılan: 1)"
)
async def key_slash(interaction: discord.Interaction, sure: str, adet: int = 1):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return

    if adet > 20:
        await interaction.response.send_message("❌ Bir seferde en fazla 20 anahtar oluşturabilirsiniz.", ephemeral=True)
        return

    try:
        keys_generated = []
        sure_lower = sure.lower().replace("ı", "i")
        is_unlimited = (sure_lower == "sinirsiz")
        
        if not is_unlimited:
            try:
                gun = int(sure)
            except ValueError:
                await interaction.response.send_message("❌ Süre hatalı! Lütfen sadece sayı (Örn: 30) veya 'sinirsiz' yazın.", ephemeral=True)
                return
        else:
            gun = "unlimited"

        for _ in range(adet):
            if is_unlimited:
                # Format: XXXX-XXXX-XXXX-XXXX (4'lü)
                key_parts = [''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4)]
            else:
                # Format: XXXX-XXXX-XXXX (3'lü)
                key_parts = [''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
            new_key = "-".join(key_parts)
            
            ref = db.reference(f'keys/{new_key}')
            ref.set({
                'days': gun,
                'used': False,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': str(interaction.user)
            })
            keys_generated.append(new_key)
            
        keys_str = "\n".join([f"`{k}`" for k in keys_generated])
        sure_text = "♾️ SINIRSIZ" if is_unlimited else f"{gun} Günlük"
        
        await interaction.user.send(f"✅ **{adet} Adet {sure_text} Lisans Anahtarı Oluşturuldu:**\n\n{keys_str}")
        await interaction.response.send_message("✅ Anahtarlar oluşturuldu ve size Özel Mesaj (DM) olarak gönderildi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Veritabanı Hatası: {e}", ephemeral=True)


# TOKEN bilgisini .env dosyasından al
TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "SENIN_DISCORD_BOT_TOKEN_BURAYA_GELECEK":
        print("LÜTFEN .env DOSYASININ İÇİNE GİRİP DISCORD_TOKEN KISMINA KENDİ BOT TOKENİNİ YAPIŞTIR!")
    else:
        keep_alive() # Web sunucusunu başlat (Render için 7/24 uyanık tutar)
        bot.run(TOKEN)

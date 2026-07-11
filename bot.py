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
activity = discord.Game(name="Charon Project")
bot = commands.Bot(command_prefix='!', intents=intents, activity=activity, status=discord.Status.dnd)

@bot.event
async def on_ready():
    print('-----------------------------------------', flush=True)
    print(f'> Discord botu DND modunda aktif: {bot.user}', flush=True)
    print('> Firebase bulut baglantisi basarili!', flush=True)
    print('-----------------------------------------', flush=True)

@bot.command()
async def onayla(ctx, username: str):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Yetkiniz yok!")
        return

    clean_username = "".join(c for c in username if c.isalnum()).lower()
    try:
        ref = db.reference(f'users/{clean_username}')
        user_data = ref.get()
        if not user_data:
            await ctx.send(f"❌ '{username}' adlı bir kullanıcı bulunamadı! Lütfen önce uygulamadan kayıt olsun.")
            return
            
        ref.update({
            'license_expiry': 'unlimited'
        })
        await ctx.send(f"✅ Başarılı! `{username}` hesabı için **Sınırsız** lisans tanımlandı.", delete_after=10)
        
        # Kanalı temizle (Sabitli mesajlar hariç)
        await ctx.channel.purge(check=lambda m: not m.pinned, limit=100)
    except Exception as e:
        await ctx.send(f"❌ Veritabanı Hatası: {e}")

@bot.command()
async def sureli(ctx, username: str, gun: int):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Yetkiniz yok!")
        return

    clean_username = "".join(c for c in username if c.isalnum()).lower()
    try:
        ref = db.reference(f'users/{clean_username}')
        user_data = ref.get()
        if not user_data:
            await ctx.send(f"❌ '{username}' adlı bir kullanıcı bulunamadı! Lütfen önce uygulamadan kayıt olsun.")
            return

        current_expiry = user_data.get('license_expiry', 'none')
        start_date = datetime.now()
        if current_expiry != "none" and current_expiry != "unlimited":
            try:
                existing_end = datetime.strptime(current_expiry, '%Y-%m-%d')
                if existing_end > start_date:
                    start_date = existing_end
            except: pass
            
        bitis_tarihi = (start_date + timedelta(days=gun)).strftime('%Y-%m-%d')
        ref.update({
            'license_expiry': bitis_tarihi
        })
        await ctx.send(f"✅ Başarılı! `{username}` hesabına **{gun} günlük** ek lisans tanımlandı. (Bitiş: {bitis_tarihi})", delete_after=10)
        
        # Kanalı temizle (Sabitli mesajlar hariç)
        await ctx.channel.purge(check=lambda m: not m.pinned, limit=100)
    except Exception as e:
        await ctx.send(f"❌ Veritabanı Hatası: {e}")

@bot.command()
async def sil(ctx, username: str):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Yetkiniz yok!")
        return
        
    clean_username = "".join(c for c in username if c.isalnum()).lower()
    try:
        ref = db.reference(f'users/{clean_username}')
        user_data = ref.get()
        if not user_data:
            await ctx.send(f"❌ '{username}' adlı bir kullanıcı bulunamadı!")
            return
            
        ref.update({
            'license_expiry': 'none'
        })
        await ctx.send(f"🗑️ `{username}` hesabının lisansı iptal edildi.")
    except Exception as e:
        await ctx.send(f"❌ Veritabanı Hatası: {e}")

import random
import string

@bot.command()
async def key_olustur(ctx, gun: int = 30, adet: int = 1):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Yetkiniz yok!")
        return

    if adet > 20:
        await ctx.send("❌ Bir seferde en fazla 20 anahtar oluşturabilirsiniz.")
        return

    try:
        keys_generated = []
        for _ in range(adet):
            # Format: XXXX-XXXX-XXXX
            key_parts = [''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
            new_key = "-".join(key_parts)
            
            ref = db.reference(f'keys/{new_key}')
            ref.set({
                'days': gun,
                'used': False,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': str(ctx.author)
            })
            keys_generated.append(new_key)
            
        keys_str = "\n".join([f"`{k}`" for k in keys_generated])
        await ctx.author.send(f"✅ **{adet} Adet {gun} Günlük Lisans Anahtarı Oluşturuldu:**\n\n{keys_str}")
        await ctx.send("✅ Anahtarlar oluşturuldu ve size Özel Mesaj (DM) olarak gönderildi.")
    except Exception as e:
        await ctx.send(f"❌ Veritabanı Hatası: {e}")

@bot.command()
async def key_olustur_unlimited(ctx, adet: int = 1):
    """Sınırsız süreli lisans anahtarı oluşturur. !key_olustur_unlimited [adet]"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Yetkiniz yok!")
        return

    if adet > 20:
        await ctx.send("❌ Bir seferde en fazla 20 anahtar oluşturabilirsiniz.")
        return

    try:
        keys_generated = []
        for _ in range(adet):
            # Format: XXXX-XXXX-XXXX-XXXX (4'lü - daha premium görünüm)
            key_parts = [''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(4)]
            new_key = "-".join(key_parts)
            
            ref = db.reference(f'keys/{new_key}')
            ref.set({
                'days': 'unlimited',
                'used': False,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'created_by': str(ctx.author)
            })
            keys_generated.append(new_key)
            
        keys_str = "\n".join([f"`{k}`" for k in keys_generated])
        await ctx.author.send(f"✅ **{adet} Adet ♾️ SINIRSIIZ Lisans Anahtarı Oluşturuldu:**\n\n{keys_str}")
        await ctx.send("✅ Sınırsız anahtarlar oluşturuldu ve size Özel Mesaj (DM) olarak gönderildi.")
    except Exception as e:
        await ctx.send(f"❌ Veritabanı Hatası: {e}")



@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, sebep: str = "Belirtilmedi"):
    await member.ban(reason=sebep)
    await ctx.send(f"🔨 **{member.name}** sunucudan yasaklandı! Sebep: {sebep}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, sebep: str = "Belirtilmedi"):
    await member.kick(reason=sebep)
    await ctx.send(f"👢 **{member.name}** sunucudan atıldı! Sebep: {sebep}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, sure_dakika: int = 720, *, sebep: str = "Belirtilmedi"):
    # Varsayılan 720 dakika = 12 saat
    duration = timedelta(minutes=sure_dakika)
    await member.timeout(duration, reason=sebep)
    await ctx.send(f"🔇 **{member.name}**, {sure_dakika} dakika boyunca susturuldu! Sebep: {sebep}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 **{member.name}** susturması kaldırıldı!")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def temizle(ctx, sayi: int):
    await ctx.channel.purge(limit=sayi + 1)
    await ctx.send(f"🧹 **{sayi}** adet mesaj temizlendi!", delete_after=5)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, saniye: int):
    await ctx.channel.edit(slowmode_delay=saniye)
    await ctx.send(f"⏳ Kanal yavaş modu **{saniye} saniye** olarak ayarlandı.")

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    pos = ctx.channel.position
    new_channel = await ctx.channel.clone()
    await ctx.channel.delete()
    await new_channel.edit(position=pos)
    await new_channel.send("💥 Kanal başarıyla sıfırlandı! (Nuked)")

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.name for role in member.roles[1:]] # @everyone haricindeki roller
    embed = discord.Embed(title=f"Kullanıcı Bilgisi: {member.name}", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Sunucuya Katılım", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Roller", value=", ".join(roles) if roles else "Yok", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup_onay(ctx):
    # Kullanıcının istediği özel mesaj içeriği
    mesaj_icerigi = (
        "**CHARON PROJECT** yazılımını kullanabilmek için uygulamadan **Kayıt Ol** ekranından ücretsiz hesap oluşturmalısınız.\n\n"
        "Hesabınızı oluşturduktan sonra, satın aldığınız lisans anahtarını **Lisans Etkinleştir (Kod Kullan)** "
        "bölümüne girerek hesabınızı aktif edebilirsiniz.\n\n"
        "Lisans anahtarı satın almak için sitemizi ziyaret edebilir veya destek talebi oluşturabilirsiniz."
    )
    
    embed = discord.Embed(
        title="🚀 CHARON PROJECT - KAYIT VE ONAY REHBERİ",
        description=mesaj_icerigi,
        color=discord.Color.blue()
    )
    embed.set_footer(text="Charon Project Yetkili Sistemi")
    
    # Yerel logo dosyasını yükleyip thumbnail olarak ayarla
    logo_path = "../gui/web/logo.png"
    if os.path.exists(logo_path):
        file = discord.File(logo_path, filename="logo.png")
        embed.set_thumbnail(url="attachment://logo.png")
        msg = await ctx.send(file=file, embed=embed)
    else:
        msg = await ctx.send(embed=embed)
    
    try:
        await msg.pin()
        await ctx.message.delete()
        await ctx.send("✅ Kurulum mesajı logo ile birlikte gönderildi ve sabitlendi!", delete_after=3)
    except Exception as e:
        await ctx.send(f"⚠️ Mesaj gönderildi ama sabitlenemedi (Yetki hatası olabilir): {e}")

# TOKEN bilgisini .env dosyasından al
TOKEN = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "SENIN_DISCORD_BOT_TOKEN_BURAYA_GELECEK":
        print("LÜTFEN .env DOSYASININ İÇİNE GİRİP DISCORD_TOKEN KISMINA KENDİ BOT TOKENİNİ YAPIŞTIR!")
    else:
        keep_alive() # Web sunucusunu başlat (Render için 7/24 uyanık tutar)
        bot.run(TOKEN)

import os
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import find_dotenv, load_dotenv

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None

load_dotenv(find_dotenv())

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    activity=discord.Game(name="Sunucuyu koruyor"),
    status=discord.Status.online,
)


def setup_database():
    """Firebase yapılandırılmışsa uyarıları kalıcı olarak saklar."""
    if not firebase_admin or firebase_admin._apps:
        return False

    database_url = os.getenv("DATABASE_URL", "").strip()
    credentials_json = os.getenv("FIREBASE_CREDENTIALS", "").strip()
    key_path = os.getenv("FIREBASE_KEY_PATH", "").strip()
    if not database_url:
        return False

    try:
        if credentials_json:
            import json
            credential = credentials.Certificate(json.loads(credentials_json))
        elif key_path and os.path.isfile(key_path):
            credential = credentials.Certificate(key_path)
        else:
            return False
        firebase_admin.initialize_app(credential, {"databaseURL": database_url})
        return True
    except Exception as error:
        print(f"Firebase devre dışı bırakıldı: {error}")
        return False


DATABASE_READY = setup_database()
log_channels: dict[int, int] = {}


def can_moderate(interaction: discord.Interaction) -> bool:
    return bool(interaction.guild and interaction.user.guild_permissions.moderate_members)


async def require_moderator(interaction: discord.Interaction) -> bool:
    if can_moderate(interaction):
        return True
    await interaction.response.send_message("❌ Bu komut için **Üyeleri Yönet** yetkisi gerekli.", ephemeral=True)
    return False


async def require_channel_manager(interaction: discord.Interaction) -> bool:
    if interaction.guild and interaction.user.guild_permissions.manage_channels:
        return True
    await interaction.response.send_message("❌ Bu komut için **Kanalları Yönet** yetkisi gerekli.", ephemeral=True)
    return False


def hierarchy_allows(interaction: discord.Interaction, member: discord.Member) -> bool:
    me = interaction.guild.me if interaction.guild else None
    return bool(
        me
        and member != interaction.guild.owner
        and member.top_role < me.top_role
        and (interaction.user == interaction.guild.owner or member.top_role < interaction.user.top_role)
    )


async def send_log(guild: discord.Guild, embed: discord.Embed):
    channel_id = log_channels.get(guild.id)
    if DATABASE_READY:
        stored_channel_id = db.reference(f"moderation/settings/{guild.id}/log_channel_id").get()
        if stored_channel_id:
            channel_id = int(stored_channel_id)
    if not channel_id:
        fallback = os.getenv("MOD_LOG_CHANNEL_ID", "").strip()
        channel_id = int(fallback) if fallback.isdigit() else None
    if channel_id is None:
        return
    channel = guild.get_channel(channel_id)
    if isinstance(channel, discord.abc.Messageable):
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def log_action(guild: discord.Guild, action: str, target: discord.abc.User, moderator: discord.abc.User, reason: str):
    embed = discord.Embed(
        title=f"\U0001f6e1\ufe0f {action}",
        colour=discord.Colour.orange(),
        timestamp=datetime.now(timezone.utc),
    )
    guild_icon = guild.icon.url if guild.icon else None
    embed.set_author(name=f"Moderasyon Kaydi | {guild.name}", icon_url=guild_icon)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="\U0001f464 Uye", value=f"{target.mention}\n`{target.id}`", inline=True)
    embed.add_field(name="\U0001f6e1\ufe0f Yetkili", value=moderator.mention, inline=True)
    embed.add_field(name="\U0001f4dd Sebep", value=reason[:1024], inline=False)
    embed.set_footer(text="Moderasyon gunlugu")
    await send_log(guild, embed)
    return
    embed = discord.Embed(title=f"🛡️ Moderasyon: {action}", colour=discord.Colour.orange(), timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Üye", value=f"{target.mention} (`{target.id}`)", inline=False)
    embed.add_field(name="Yetkili", value=f"{moderator.mention}", inline=True)
    embed.add_field(name="Sebep", value=reason, inline=True)
    await send_log(guild, embed)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot or before.channel == after.channel:
        return
    if before.channel is None:
        action, detail = "Sesliye katildi", after.channel.mention
    elif after.channel is None:
        action, detail = "Sesliden ayrildi", before.channel.mention
    else:
        action, detail = "Sesli kanal degistirdi", f"{before.channel.mention} -> {after.channel.mention}"
    colour = discord.Colour.green() if before.channel is None else discord.Colour.red() if after.channel is None else discord.Colour.blurple()
    embed = discord.Embed(title=f"\U0001f50a {action}", colour=colour, timestamp=datetime.now(timezone.utc))
    guild_icon = member.guild.icon.url if member.guild.icon else None
    embed.set_author(name=f"Ses Kaydi | {member.guild.name}", icon_url=guild_icon)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="\U0001f464 Uye", value=f"{member.mention}\n`{member.id}`", inline=True)
    embed.add_field(name="\U0001f50a Kanal", value=detail, inline=True)
    embed.set_footer(text="Sesli kanal gunlugu")
    await send_log(member.guild, embed)
    return
    """Yalnızca sesli kanala katılma, ayrılma ve kanal değiştirme olaylarını kaydeder."""
    if member.bot or before.channel == after.channel:
        return
    if before.channel is None:
        action, detail = "Sesliye katıldı", after.channel.mention
    elif after.channel is None:
        action, detail = "Sesliden ayrıldı", before.channel.mention
    else:
        action, detail = "Sesli kanal değiştirdi", f"{before.channel.mention} → {after.channel.mention}"
    embed = discord.Embed(title=f"🔊 {action}", colour=discord.Colour.teal(), timestamp=datetime.now(timezone.utc))
    embed.add_field(name="Üye", value=f"{member.mention} (`{member.id}`)", inline=False)
    embed.add_field(name="Kanal", value=detail, inline=False)
    await send_log(member.guild, embed)


@bot.event
async def on_ready():
    print(f"{bot.user} moderasyon botu olarak hazır.")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as error:
        print(f"Komut senkronizasyon hatası: {error}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Discord izin/hiyerarşi hatalarında kullanıcıya anlaşılır geri bildirim verir."""
    if isinstance(error, app_commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
        message = "❌ Botun bu işlem için gerekli izni yok veya botun rolü hedef üyeden daha aşağıda."
    elif isinstance(error, app_commands.CommandInvokeError) and isinstance(error.original, discord.HTTPException):
        message = "❌ Discord işlemi tamamlayamadı. Lütfen tekrar deneyin."
    else:
        print(f"Komut hatası: {error}")
        message = "❌ Komut işlenirken bir hata oluştu."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name="yardim", description="Moderasyon komutlarını gösterir.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ Moderasyon Komutları", colour=discord.Colour.blurple())
    embed.description = (
        "`/uyar`, `/uyarilar`, `/uyarilari-temizle`\n"
        "`/zaman-asimi`, `/zaman-asimi-kaldir`\n"
        "`/at`, `/yasakla`, `/yasak-kaldir`, `/temizle`\n\n"
        "`/kilitle`, `/kilit-ac`, `/log-kanal`, `/log-kanal-kapat`\n\n"
        "Moderasyon komutları **Üyeleri Yönet**; kanal ve log ayarları **Kanalları Yönet** yetkisi gerektirir."
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="log-kanal", description="Moderasyon ve ses olaylarının gönderileceği kanalı ayarlar.")
@app_commands.describe(kanal="Logların gönderileceği metin kanalı")
async def set_log_channel(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not await require_channel_manager(interaction): return
    log_channels[interaction.guild.id] = kanal.id
    if DATABASE_READY:
        db.reference(f"moderation/settings/{interaction.guild.id}/log_channel_id").set(kanal.id)
    await interaction.response.send_message(f"✅ Log kanalı {kanal.mention} olarak ayarlandı.", ephemeral=True)
    await log_action(interaction.guild, "Log kanalı ayarlandı", interaction.user, interaction.user, kanal.mention)


@bot.tree.command(name="log-kanal-kapat", description="Sunucu için log gönderimini kapatır.")
async def disable_log_channel(interaction: discord.Interaction):
    if not await require_channel_manager(interaction): return
    log_channels.pop(interaction.guild.id, None)
    if DATABASE_READY:
        db.reference(f"moderation/settings/{interaction.guild.id}/log_channel_id").delete()
    await interaction.response.send_message("✅ Log gönderimi kapatıldı.", ephemeral=True)


@bot.tree.command(name="kilitle", description="Bir metin kanalında @everyone mesaj gönderimini kapatır.")
@app_commands.describe(kanal="Boş bırakırsanız bulunduğunuz kanal kilitlenir", sebep="İsteğe bağlı kilitleme sebebi")
async def lock_channel(interaction: discord.Interaction, kanal: discord.TextChannel | None = None, sebep: str = "Belirtilmedi"):
    if not await require_channel_manager(interaction): return
    target = kanal or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.response.send_message("❌ Bir metin kanalı seçin veya komutu metin kanalında kullanın.", ephemeral=True); return
    overwrite = target.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await target.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"{interaction.user}: {sebep}")
    await interaction.response.send_message(f"🔒 {target.mention} kilitlendi.")
    await log_action(interaction.guild, "Kanal kilitlendi", interaction.user, interaction.user, f"{target.mention} — {sebep}")


@bot.tree.command(name="kilit-ac", description="Bir metin kanalında @everyone mesaj gönderimini tekrar açar.")
@app_commands.describe(kanal="Boş bırakırsanız bulunduğunuz kanalın kilidi açılır", sebep="İsteğe bağlı açma sebebi")
async def unlock_channel(interaction: discord.Interaction, kanal: discord.TextChannel | None = None, sebep: str = "Belirtilmedi"):
    if not await require_channel_manager(interaction): return
    target = kanal or interaction.channel
    if not isinstance(target, discord.TextChannel):
        await interaction.response.send_message("❌ Bir metin kanalı seçin veya komutu metin kanalında kullanın.", ephemeral=True); return
    overwrite = target.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await target.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"{interaction.user}: {sebep}")
    await interaction.response.send_message(f"🔓 {target.mention} kilidi açıldı.")
    await log_action(interaction.guild, "Kanal kilidi açıldı", interaction.user, interaction.user, f"{target.mention} — {sebep}")


@bot.tree.command(name="uyar", description="Bir üyeye uyarı verir.")
@app_commands.describe(uye="Uyarılacak üye", sebep="Uyarı sebebi")
async def warn(interaction: discord.Interaction, uye: discord.Member, sebep: str):
    if not await require_moderator(interaction): return
    if not hierarchy_allows(interaction, uye):
        await interaction.response.send_message("❌ Bu üyeyi yönetemezsiniz.", ephemeral=True); return
    warning = {"reason": sebep, "moderator": str(interaction.user), "moderator_id": interaction.user.id, "created_at": datetime.now(timezone.utc).isoformat()}
    if DATABASE_READY:
        db.reference(f"moderation/warnings/{interaction.guild.id}/{uye.id}").push(warning)
    try: await uye.send(f"⚠️ **{interaction.guild.name}** sunucusunda uyarıldınız.\nSebep: {sebep}")
    except discord.Forbidden: pass
    await log_action(interaction.guild, "Uyarı", uye, interaction.user, sebep)
    await interaction.response.send_message(f"⚠️ {uye.mention} uyarıldı.")


@bot.tree.command(name="uyarilar", description="Bir üyenin kayıtlı uyarılarını gösterir.")
async def warnings(interaction: discord.Interaction, uye: discord.Member):
    if not await require_moderator(interaction): return
    records = db.reference(f"moderation/warnings/{interaction.guild.id}/{uye.id}").get() if DATABASE_READY else None
    if not records:
        await interaction.response.send_message(f"{uye.mention} için kayıtlı uyarı yok.", ephemeral=True); return
    values = list(records.values())[-10:]
    lines = [f"• {item['reason']} — {item['moderator']}" for item in values]
    await interaction.response.send_message(f"⚠️ **{uye}** için son {len(lines)} uyarı:\n" + "\n".join(lines), ephemeral=True)


@bot.tree.command(name="uyarilari-temizle", description="Bir üyenin tüm uyarı kayıtlarını siler.")
async def clear_warnings(interaction: discord.Interaction, uye: discord.Member):
    if not await require_moderator(interaction): return
    if DATABASE_READY: db.reference(f"moderation/warnings/{interaction.guild.id}/{uye.id}").delete()
    await interaction.response.send_message(f"✅ {uye.mention} için uyarı kayıtları temizlendi.", ephemeral=True)


@bot.tree.command(name="zaman-asimi", description="Bir üyeyi geçici olarak susturur.")
@app_commands.describe(uye="Susturulacak üye", dakika="Süre (1-40320 dakika)", sebep="Sebep")
async def timeout(interaction: discord.Interaction, uye: discord.Member, dakika: app_commands.Range[int, 1, 40320], sebep: str):
    if not await require_moderator(interaction): return
    if not hierarchy_allows(interaction, uye):
        await interaction.response.send_message("❌ Bu üyeyi yönetemezsiniz.", ephemeral=True); return
    await uye.timeout(timedelta(minutes=dakika), reason=f"{interaction.user}: {sebep}")
    await log_action(interaction.guild, f"Zaman aşımı ({dakika} dk)", uye, interaction.user, sebep)
    await interaction.response.send_message(f"🔇 {uye.mention}, {dakika} dakika zaman aşımına alındı.")


@bot.tree.command(name="zaman-asimi-kaldir", description="Bir üyenin zaman aşımını kaldırır.")
async def remove_timeout(interaction: discord.Interaction, uye: discord.Member, sebep: str = "Belirtilmedi"):
    if not await require_moderator(interaction): return
    if not hierarchy_allows(interaction, uye):
        await interaction.response.send_message("❌ Bu üyeyi yönetemezsiniz.", ephemeral=True); return
    await uye.timeout(None, reason=f"{interaction.user}: {sebep}")
    await log_action(interaction.guild, "Zaman aşımı kaldırıldı", uye, interaction.user, sebep)
    await interaction.response.send_message(f"🔊 {uye.mention} için zaman aşımı kaldırıldı.")


@bot.tree.command(name="at", description="Bir üyeyi sunucudan atar.")
async def kick(interaction: discord.Interaction, uye: discord.Member, sebep: str = "Belirtilmedi"):
    if not await require_moderator(interaction): return
    if not hierarchy_allows(interaction, uye):
        await interaction.response.send_message("❌ Bu üyeyi yönetemezsiniz.", ephemeral=True); return
    await log_action(interaction.guild, "Atıldı", uye, interaction.user, sebep)
    await uye.kick(reason=f"{interaction.user}: {sebep}")
    await interaction.response.send_message(f"👢 {uye} sunucudan atıldı.")


@bot.tree.command(name="yasakla", description="Bir üyeyi sunucudan yasaklar.")
async def ban(interaction: discord.Interaction, uye: discord.Member, sebep: str = "Belirtilmedi", mesajlari_sil: app_commands.Range[int, 0, 7] = 0):
    if not await require_moderator(interaction): return
    if not hierarchy_allows(interaction, uye):
        await interaction.response.send_message("❌ Bu üyeyi yönetemezsiniz.", ephemeral=True); return
    await log_action(interaction.guild, "Yasaklandı", uye, interaction.user, sebep)
    await uye.ban(reason=f"{interaction.user}: {sebep}", delete_message_days=mesajlari_sil)
    await interaction.response.send_message(f"🔨 {uye} yasaklandı.")


@bot.tree.command(name="yasak-kaldir", description="Kullanıcı ID'siyle yasağı kaldırır.")
async def unban(interaction: discord.Interaction, kullanici_id: str, sebep: str = "Belirtilmedi"):
    if not await require_moderator(interaction): return
    try:
        user = await bot.fetch_user(int(kullanici_id))
        await interaction.guild.unban(user, reason=f"{interaction.user}: {sebep}")
    except (ValueError, discord.NotFound):
        await interaction.response.send_message("❌ Geçerli ve yasaklı bir kullanıcı ID'si girin.", ephemeral=True); return
    await log_action(interaction.guild, "Yasağı kaldırıldı", user, interaction.user, sebep)
    await interaction.response.send_message(f"✅ {user} için yasak kaldırıldı.")


@bot.tree.command(name="temizle", description="Kanaldaki son mesajları siler.")
async def purge(interaction: discord.Interaction, adet: app_commands.Range[int, 1, 100]):
    if not await require_moderator(interaction): return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("❌ Bu komut yalnızca metin kanallarında kullanılabilir.", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=adet)
    await interaction.followup.send(f"🧹 {len(deleted)} mesaj silindi.", ephemeral=True)
    await log_action(interaction.guild, f"Mesaj temizleme ({len(deleted)})", interaction.user, interaction.user, f"#{interaction.channel.name}")


TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN .env içinde ayarlanmalı.")
    from keep_alive import keep_alive
    keep_alive()
    bot.run(TOKEN)

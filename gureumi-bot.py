import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
import asyncio

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_ID = 서버id

USER_MONEY_FILE = "user_money.json"
ROLE_SHOP_FILE = "role_shop.json"
TRANSACTION_LOG_FILE = "transactions.json"
VOICE_CHANNELS_FILE = "voice_channels.json"
VOICE_ACTIVITY_FILE = "voice_activity.json"

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

user_money = load_json(USER_MONEY_FILE)
role_shop = load_json(ROLE_SHOP_FILE)
transaction_log = load_json(TRANSACTION_LOG_FILE)
voice_channels = load_json(VOICE_CHANNELS_FILE)
voice_activity = load_json(VOICE_ACTIVITY_FILE)
if "channels" not in voice_channels:
    voice_channels["channels"] = []

def save_voice_activity():
    save_json(VOICE_ACTIVITY_FILE, voice_activity)

def save_user_money():
    save_json(USER_MONEY_FILE, user_money)

def save_role_shop():
    save_json(ROLE_SHOP_FILE, role_shop)

def save_voice_channels():
    save_json(VOICE_CHANNELS_FILE, voice_channels)

def log_transaction(user_id, detail):
    user_id = str(user_id)
    if user_id not in transaction_log:
        transaction_log[user_id] = []
    transaction_log[user_id].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "detail": detail
    })
    save_json(TRANSACTION_LOG_FILE, transaction_log)

def create_embed(title, description, color=discord.Color.blue(), fields=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value, inline in fields:
             embed.add_field(name=name, value=value, inline=inline)
             embed.set_footer(text="📫kyana03147@gmail.com")
    return embed

@bot.event
async def on_ready():
    if not hasattr(bot, 'voice_task_started'):
        voice_reward_task.start()
        bot.voice_task_started = True

    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ 봇 로그인 완료: {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    uid = str(member.id)
    now = datetime.utcnow().timestamp()

    if after.channel and after.channel.id in voice_channels["channels"]:
        voice_activity[uid] = now
        save_voice_activity()
    elif not after.channel:
        voice_activity.pop(uid, None)
        save_voice_activity()

@tasks.loop(minutes=1)
async def voice_reward_task():
    now = datetime.utcnow().timestamp()
    for uid, joined_at in list(voice_activity.items()):
        if now - joined_at >= 600:
            voice_activity[uid] = now
            user_money[uid] = user_money.get(uid, 0) + 20
            log_transaction(uid, "구름빵 획득 채널 접속 보상: +20 ☁️")
    save_user_money()
    save_voice_activity()

@bot.tree.command(name="채널추가", description="구름빵 획득 채널을 추가합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="음성 채널")
async def 채널추가(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if channel.id not in voice_channels["channels"]:
        voice_channels["channels"].append(channel.id)
        save_voice_channels()
        embed = create_embed("☁️ 구름빵 획득 채널 추가됨", f"{channel.mention} 채널이 ☁️ 구름빵 획득 채널로 등록되었습니다.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = create_embed("⚠️ 중복 등록", f"{channel.mention} 채널은 이미 등록되어 있습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="채널삭제", description="구름빵 획득 채널을 제거합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="음성 채널")
async def 채널삭제(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if channel.id in voice_channels["channels"]:
        voice_channels["channels"].remove(channel.id)
        save_voice_channels()
        embed = create_embed("🗑️ 보상 채널 제거됨", f"{channel.mention} ☁️ 구름빵 획득 채널 목록에서 제거되었습니다.")
        await interaction.response.send_message(embed=embed)
    else:
        embed = create_embed("⚠️ 채널 미등록", f"{channel.mention} 채널은 등록되어 있지 않습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="채널목록", description="현재 등록된 구름빵 획득 채널 목록을 확인합니다", guild=discord.Object(id=GUILD_ID))
async def 채널목록(interaction: discord.Interaction):
    if not voice_channels["channels"]:
        await interaction.response.send_message("☁️ 구름빵 획득 채널이 없습니다.")
        return

    lines = []
    for ch_id in voice_channels["channels"]:
        channel = interaction.guild.get_channel(ch_id)
        if channel:
            lines.append(f"- <#{ch_id}>")
        else:
            lines.append(f"- (삭제된 채널) `{ch_id}`")

    description = "\n".join(lines)
    embed = create_embed("☁️ 구름빵 획득 채널", description)
    await interaction.response.send_message(embed=embed)


# 관리자 명령어
@bot.tree.command(name="지급", description="유저에게 구름빵을 지급합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="지급할 유저", amount="금액")
async def 지급(interaction: discord.Interaction, user: discord.User, amount: int):
    user_money[str(user.id)] = user_money.get(str(user.id), 0) + amount
    save_user_money()
    log_transaction(user.id, f"✅ 관리자 지급: +{amount:,} ☁️")
    embed = create_embed("💸 지급 완료", f"{user.mention}에게 {amount:,} ☁️을 지급했습니다.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="회수", description="유저의 구름빵을 회수합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="회수할 유저", amount="금액")
async def 회수(interaction: discord.Interaction, user: discord.User, amount: int):
    user_money[str(user.id)] = max(user_money.get(str(user.id), 0) - amount, 0)
    save_user_money()
    log_transaction(user.id, f"❌ 관리자 회수: -{amount:,} ☁️")
    embed = create_embed("🧾 회수 완료", f"{user.mention}의 구름빵 {amount:,} ☁️을 회수했습니다.", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="상품등록", description="상점에 상품 역할을 등록합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(name="상품 이름", price="가격", role="부여할 역할")
async def 상품등록(interaction: discord.Interaction, name: str, price: int, role: discord.Role):
    role_shop[name] = {"price": price, "role_id": role.id}
    save_role_shop()
    embed = create_embed("🛒 등록 완료", f"상품 {name}이(가) {price:,} ☁️에 등록되었습니다.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="상품제거", description="등록된 상품을 제거합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(name="제거할 상품 이름")
async def 상품제거(interaction: discord.Interaction, name: str):
    if name not in role_shop:
        await interaction.response.send_message("⚠️ 존재하지 않는 상품입니다.", ephemeral=True)
        return
    del role_shop[name]
    save_role_shop()
    await interaction.response.send_message(f"🗑️ '{name}' 상품이 제거되었습니다.", ephemeral=True)

@상품제거.autocomplete("name")
async def autocomplete_delete_products(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=p, value=p)
        for p in role_shop.keys() if current.lower() in p.lower()
    ][:25]

@bot.tree.command(name="데이터삭제", description="유저의 데이터를 삭제합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="삭제할 유저")
async def 데이터삭제(interaction: discord.Interaction, user: discord.User):
    user_id = str(user.id)
    user_money.pop(user_id, None)
    transaction_log.pop(user_id, None)
    save_user_money()
    save_json(TRANSACTION_LOG_FILE, transaction_log)
    await interaction.response.send_message(f"🧼 {user.mention}의 데이터가 삭제되었습니다.", ephemeral=True)

@bot.tree.command(name="구매", description="상품을 구매합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(name="구매할 상품 이름")
async def 구매(interaction: discord.Interaction, name: str):
    user_id = str(interaction.user.id)
    if name not in role_shop:
        embed = create_embed("⚠️ 오류", "존재하지 않는 상품입니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    product = role_shop[name]
    price = product["price"]
    role = interaction.guild.get_role(product["role_id"])

    if user_money.get(user_id, 0) < price:
        embed = create_embed("☁️ 잔액 부족", "잔액이 부족합니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if role in interaction.user.roles:
        embed = create_embed("⚠️ 오류", "이미 해당 상품을 보유하고 있습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    user_money[user_id] -= price
    await interaction.user.add_roles(role)
    save_user_money()
    log_transaction(user_id, f"🛒 {name} 역할 구매 (-{price:,} ☁️)")

    embed = create_embed("✅ 구매 성공", f"'{name}' 을 구매했습니다.", fields=[
        ("차감 구름빵", f"{price:,} ☁️", True),
        ("잔여 구름빵", f"{user_money[user_id]:,} ☁️", True)
    ])
    await interaction.response.send_message(embed=embed)

@구매.autocomplete("name")
async def autocomplete_products(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=p, value=p)
        for p in role_shop.keys() if current.lower() in p.lower()
    ][:25]

@bot.tree.command(name="잔액확인", description="자신의 잔액을 확인합니다", guild=discord.Object(id=GUILD_ID))
async def 잔액확인(interaction: discord.Interaction):
    money = user_money.get(str(interaction.user.id), 0)
    embed = create_embed("☁️ 보유 구름빵", f"{interaction.user.mention}님은 현재 {money:,} ☁️을 보유 중입니다.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="송금", description="다른 유저에게 구름빵을 송금합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="받을 유저", amount="금액")
async def 송금(interaction: discord.Interaction, user: discord.User, amount: int):
    sender_id = str(interaction.user.id)
    receiver_id = str(user.id)
    if user == interaction.user:
        await interaction.response.send_message("⚠️ 자신에게는 송금할 수 없습니다.", ephemeral=True)
        return
    if user_money.get(sender_id, 0) < amount:
        await interaction.response.send_message("⚠️ 잔액이 부족합니다.", ephemeral=True)
        return

    user_money[sender_id] -= amount
    user_money[receiver_id] = user_money.get(receiver_id, 0) + amount
    save_user_money()
    log_transaction(sender_id, f"📤 {user.mention}에게 송금 (-{amount:,} ☁️)")
    log_transaction(receiver_id, f"📥 {interaction.user.mention}에게 송금 (+{amount:,} ☁️)")
    await interaction.response.send_message(f"✅ {user.mention}에게 {amount:,} ☁️을 송금했습니다.")

@bot.tree.command(name="상점", description="상점 목록을 확인합니다", guild=discord.Object(id=GUILD_ID))
async def 상점(interaction: discord.Interaction):
    if not role_shop:
        embed = create_embed("📭 상점이 비어 있습니다", "등록된 상품이 없습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = create_embed("💌 상품 목록", "아래는 구매 가능한 상품 목록입니다:")
    for name, info in role_shop.items():
        role = interaction.guild.get_role(info['role_id'])
        if role:
            embed.add_field(
                name=name,
                value=f"{role.mention}\n☁️ {info['price']:,}",
                inline=False
            )
        else:
            embed.add_field(
                name=name,
                value=f"(역할 없음)\n☁️ {info['price']:,}",
                inline=False
            )

    await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions(roles=False))

@bot.tree.command(name="유저검색", description="유저의 잔액을 검색합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="검색할 유저")
async def 유저검색(interaction: discord.Interaction, user: discord.User):
    money = user_money.get(str(user.id), 0)
    embed = create_embed("🔍 유저 잔액 조회", f"{user.mention}의 보유 잔액은 {money:,} ☁️입니다.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="거래내역", description="유저의 거래내역을 조회합니다", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="유저")
async def 거래내역(interaction: discord.Interaction, user: discord.User):
    logs = transaction_log.get(str(user.id), [])
    if not logs:
        await interaction.response.send_message("📭 거래 내역이 없습니다.", ephemeral=True)
        return

    embed = create_embed("📜 거래 내역", f"{user.mention}의 최근 거래 기록:")
    for entry in logs[-10:][::-1]:
        embed.add_field(name=entry["time"], value=entry["detail"], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="랭킹", description="보유 구름빵 순위 상위 10명", guild=discord.Object(id=GUILD_ID))
async def 랭킹(interaction: discord.Interaction):
    top = sorted(user_money.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = create_embed("🏆 구름빵 랭킹 Top 10", "")
    for i, (user_id, amount) in enumerate(top, start=1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(name=f"{i}위: {user.name}", value=f"{amount:,} ☁️", inline=False)
    await interaction.response.send_message(embed=embed)

@지급.error
@회수.error
@상품등록.error
@상품제거.error
@데이터삭제.error
@유저검색.error
@거래내역.error
async def admin_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("🚫 이 명령어는 구르미만 사용할 수 있습니다.", ephemeral=True)

bot.run("봇 토큰 입력")

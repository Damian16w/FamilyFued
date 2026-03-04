import os
import discord
from discord.ext import commands
from collections import Counter, defaultdict
import math
import requests
import dotenv

dotenv.load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Set your Discord bot token here or via environment variable
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

survey_open = False
submissions_by_user = defaultdict(list)  # user_id -> [answers]


def scale_to_hundred(counter: Counter) -> list:
    """Convert raw counts to a list of {text, points} summing to 100.
    We use proportional rounding and fix rounding drift on the top item.
    """
    items = counter.most_common()
    total = sum(count for _, count in items)
    if total == 0:
        return []
    rough = []
    accum = 0
    for text, count in items:
        pts = (count / total) * 100
        rounded = int(round(pts))
        rough.append({"text": text, "points": rounded})
        accum += rounded
    # Adjust drift to ensure sum == 100
    diff = 100 - accum
    if diff != 0:
        # bump the highest raw count item (first item)
        rough[0]["points"] += diff
    # remove zero-point tails if any accidental zeros
    rough = [r for r in rough if r["points"] > 0]
    return rough


@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")


@bot.command()
async def start_survey(ctx):
    global survey_open, submissions_by_user
    survey_open = True
    submissions_by_user = defaultdict(list)
    await ctx.send("🎯 **Survey started!** You can submit up to 3 answers with `!a <your answer>`. Use `!my` to see how many you've used.")


@bot.command()
async def a(ctx, *, answer: str):
    if not survey_open:
        await ctx.send("❌ No survey is active. Ask the host to run `!start_survey`.")
        return
    user_key = str(ctx.author.id)
    # Enforce up to 3 answers per user
    if len(submissions_by_user[user_key]) >= 3:
        await ctx.send("⛔ You have already submitted 3 answers for this survey.")
        return
    normalized = answer.strip().lower()
    if not normalized:
        await ctx.send("⚠️ Please provide a non-empty answer.")
        return
    submissions_by_user[user_key].append(normalized)
    await ctx.send(f"✅ Recorded: **{answer.strip()}**  —  ({len(submissions_by_user[user_key])}/3)")


@bot.command()
async def my(ctx):
    user_key = str(ctx.author.id)
    used = len(submissions_by_user[user_key])
    await ctx.send(f"🧮 You have used **{used}/3** submissions.")


@bot.command()
async def end_survey(ctx):
    global survey_open
    if not survey_open:
        await ctx.send("❌ No survey is active.")
        return
    survey_open = False

    # Aggregate and scale
    all_answers = []
    for answers in submissions_by_user.values():
        all_answers.extend(answers)
    counter = Counter(all_answers)

    scaled = scale_to_hundred(counter)

    # POST to backend
    try:
        resp = requests.post(f"{BACKEND_URL}/api/survey_results", json={"answers": scaled}, timeout=10)
        if resp.status_code == 200:
            await ctx.send("📊 Survey closed. Results sent to the game!")
            # Show a compact preview
            preview = "\n".join([f"{i+1}. {x['text']} — {x['points']}" for i, x in enumerate(scaled[:10])])
            if not preview:
                preview = "(no answers)"
            await ctx.send(f"**Top answers:**\n{preview}")
        else:
            await ctx.send(f"⚠️ Backend error: {resp.status_code} {resp.text}")
    except Exception as e:
        await ctx.send(f"⚠️ Failed to reach backend: {e}")


bot.run(TOKEN)
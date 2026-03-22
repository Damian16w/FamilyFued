import os
import discord
from discord.ext import commands
from collections import Counter, defaultdict
import math
import requests
import dotenv
import asyncio

dotenv.load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

survey_open = False
submissions_by_user = defaultdict(list)  # user_id -> [answers]
team_assignments = {}  # user_id -> team name
waiting_for_team = {}  # user_id -> True if waiting for team assignment

# Team configuration
TEAMS = ["Team 1", "Team 2", "Team 3"]
TEAM_EMOJIS = {
    "Team 1": "🔴",
    "Team 2": "🔵",
    "Team 3": "🟢"
}

def scale_to_hundred(counter: Counter) -> list:
    """Convert raw counts to a list of {text, points} summing to 100."""
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
    diff = 100 - accum
    if diff != 0:
        rough[0]["points"] += diff
    rough = [r for r in rough if r["points"] > 0]
    return rough

@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    print(f"Commands: !start_survey, !a, !my, !end_survey, !join, !leave, !teams, !assign_team, !balance_teams, !clear_channel, !clear_all_channels, !clear_team_channel")
    print(f"Teams: {', '.join(TEAMS)}")

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
async def join(ctx):
    """Join a team - will be assigned by host"""
    user_id = str(ctx.author.id)
    if user_id in team_assignments:
        await ctx.send(f"ℹ️ You are already on **{team_assignments[user_id]}**! Use `!leave` if you want to switch teams.")
        return
    
    waiting_for_team[user_id] = True
    await ctx.send(f"👋 {ctx.author.mention}, you've requested to join a team! The host will assign you shortly with `!assign_team @user Team 1/2/3` or use `!balance_teams` to auto-assign all waiting players.")

@bot.command()
async def leave(ctx):
    """Leave your current team"""
    user_id = str(ctx.author.id)
    if user_id in team_assignments:
        old_team = team_assignments.pop(user_id)
        await ctx.send(f"👋 {ctx.author.mention}, you've left **{old_team}**.")
        # Remove from any waiting list
        waiting_for_team.pop(user_id, None)
    else:
        await ctx.send("❌ You're not on any team!")

@bot.command()
@commands.has_permissions(administrator=True)
async def assign_team(ctx, member: discord.Member, team: str):
    """Admin command: Assign a member to a team (Team 1, Team 2, or Team 3)"""
    user_id = str(member.id)
    team = team.strip()
    
    if team not in TEAMS:
        await ctx.send(f"❌ Team must be one of: {', '.join(TEAMS)}")
        return
    
    # Check if user is already on a team
    if user_id in team_assignments:
        old_team = team_assignments[user_id]
        if old_team == team:
            await ctx.send(f"ℹ️ {member.mention} is already on {team}.")
            return
        await ctx.send(f"🔄 Moved {member.mention} from {old_team} to {team}.")
    else:
        await ctx.send(f"✅ Assigned {member.mention} to {team}!")
    
    team_assignments[user_id] = team
    waiting_for_team.pop(user_id, None)
    
    # Try to assign team role if available
    guild = ctx.guild
    role_name = team
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        try:
            await member.add_roles(role)
            await ctx.send(f"🎭 Also added {role_name} role to {member.mention}!")
        except:
            pass

@bot.command()
async def teams(ctx):
    """Show current team assignments"""
    if not team_assignments and not waiting_for_team:
        await ctx.send("📋 No players have joined teams yet. Use `!join` to join!")
        return
    
    # Group members by team
    team_members = {team: [] for team in TEAMS}
    for uid, team in team_assignments.items():
        if team in team_members:
            member = ctx.guild.get_member(int(uid))
            if member:
                team_members[team].append(member.display_name)
    
    response = "**🎮 Team Assignments**\n\n"
    for team in TEAMS:
        emoji = TEAM_EMOJIS.get(team, "📌")
        response += f"{emoji} **{team}** ({len(team_members[team])}):\n"
        if team_members[team]:
            response += "\n".join(f"  • {name}" for name in team_members[team]) + "\n\n"
        else:
            response += "  No members yet\n\n"
    
    waiting = len(waiting_for_team)
    if waiting > 0:
        response += f"\n⏳ **Waiting for assignment:** {waiting} player(s) have used `!join`\n"
        # Show waiting players
        waiting_names = []
        for uid in waiting_for_team:
            member = ctx.guild.get_member(int(uid))
            if member:
                waiting_names.append(member.display_name)
        if waiting_names:
            response += "\n".join(f"  • {name}" for name in waiting_names[:10])
            if len(waiting_names) > 10:
                response += f"\n  • ... and {len(waiting_names) - 10} more"
    
    await ctx.send(response)

@bot.command()
@commands.has_permissions(administrator=True)
async def balance_teams(ctx):
    """Admin command: Automatically balance teams across Team 1, 2, and 3"""
    if not waiting_for_team:
        await ctx.send("No players waiting for team assignment!")
        return
    
    # Count current team sizes
    team_counts = {team: 0 for team in TEAMS}
    for team in team_assignments.values():
        if team in team_counts:
            team_counts[team] += 1
    
    # Sort waiting players
    waiting_players = list(waiting_for_team.keys())
    
    # Assign to smallest team first
    assignments = []
    for user_id in waiting_players:
        # Find team with smallest size
        smallest_team = min(team_counts, key=team_counts.get)
        team_counts[smallest_team] += 1
        member = ctx.guild.get_member(int(user_id))
        if member:
            team_assignments[user_id] = smallest_team
            assignments.append(f"{member.display_name} → {smallest_team}")
            # Try to assign role
            role = discord.utils.get(ctx.guild.roles, name=smallest_team)
            if role:
                try:
                    await member.add_roles(role)
                except:
                    pass
    
    # Clear waiting list
    waiting_for_team.clear()
    
    if assignments:
        await ctx.send("⚖️ **Teams Balanced!**\n" + "\n".join(assignments))
        await teams(ctx)  # Show updated teams
    else:
        await ctx.send("No players to assign!")

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_channel(ctx, amount: int = 100):
    """Admin command: Clear messages in the current channel"""
    await ctx.send(f"🧹 Clearing last {amount} messages from this channel...")
    
    def is_not_pinned(msg):
        return not msg.pinned
    
    deleted = await ctx.channel.purge(limit=amount + 1, check=is_not_pinned)
    await ctx.send(f"✅ Cleared {len(deleted) - 1} messages!", delete_after=3)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_all_channels(ctx):
    """Admin command: Clear all text channels in the server"""
    await ctx.send("⚠️ **WARNING:** This will clear ALL text channels! Type `confirm` to proceed (this will be deleted in 10 seconds).")
    
    def check(m):
        return m.author == ctx.author and m.content.lower() == "confirm"
    
    try:
        msg = await bot.wait_for('message', timeout=10.0, check=check)
        await msg.delete()
        
        cleared_channels = []
        failed_channels = []
        
        for channel in ctx.guild.text_channels:
            try:
                await channel.purge(limit=100, check=lambda m: not m.pinned)
                cleared_channels.append(channel.name)
                await asyncio.sleep(0.5)  # Rate limit protection
            except Exception as e:
                failed_channels.append(f"{channel.name} ({str(e)})")
        
        response = f"✅ **Channel Clear Complete**\n"
        response += f"Cleared: {', '.join(cleared_channels[:10])}"
        if len(cleared_channels) > 10:
            response += f" and {len(cleared_channels) - 10} more"
        if failed_channels:
            response += f"\n❌ Failed: {', '.join(failed_channels)}"
        
        await ctx.send(response)
    except asyncio.TimeoutError:
        await ctx.send("❌ Clear cancelled - confirmation not received.")

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_team_channel(ctx, team: str):
    """Admin command: Clear messages in a specific team's voice channel text chat"""
    team = team.strip()
    if team not in TEAMS:
        await ctx.send(f"❌ Team must be one of: {', '.join(TEAMS)}")
        return
    
    # Look for text channels that might be associated with the team
    channel_name = f"{team.lower().replace(' ', '-')}-chat"
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    
    if not channel:
        await ctx.send(f"❌ Could not find channel `{channel_name}`. Make sure it exists.")
        return
    
    await channel.purge(limit=100, check=lambda m: not m.pinned)
    await ctx.send(f"✅ Cleared **{channel_name}** channel!")

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

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need administrator permissions to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required arguments! Check `!help` for usage.")
    else:
        await ctx.send(f"❌ Error: {str(error)}")

bot.run(TOKEN)
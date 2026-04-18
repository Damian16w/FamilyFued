# Family Feud Game System

Run a Family‑Feud‑style game: Discord audience submits answers, host controls from a web panel.

## Folder structure

```
rootfolder/
├── run.bat              (launches everything)
├── backend/             (Flask API)
├── discord_bot/         (Discord bot)
└── frontend/            (HTML panels)
```

## Setup

### 1. Install Python dependencies
From the `backend/` folder (or root):
```bash
pip install -r requirements.txt
```
(If no `requirements.txt` exists, run: `pip install flask flask-cors discord.py python-dotenv requests`)

### 2. Create a Discord bot
- Go to [Discord Developer Portal](https://discord.com/developers/applications)
- Click **New Application** → give it a name
- Go to **Bot** → **Add Bot**
- Under **Token**, click **Copy** (this is your `DISCORD_BOT_TOKEN`)
- Enable these **Privileged Gateway Intents**:
  - ✅ Message Content Intent
  - ✅ Server Members Intent (if you want auto‑role assignment)

### 3. Invite the bot to your server
- In Developer Portal → **OAuth2** → **URL Generator**
- Scopes: `bot`
- Bot permissions: `Send Messages`, `Read Messages`, `Manage Roles` (optional)
- Copy the generated URL, open in browser, and invite to your server

### 4. Create `.env` file
Inside the `discord_bot/` folder, create a file named `.env`:
```
DISCORD_BOT_TOKEN=paste_your_token_here
BACKEND_URL=http://127.0.0.1:5000
```

## Run the game

Double‑click **`run.bat`** – it opens two command windows (backend + bot).

- Host panel: http://localhost:5000/host
- Player screen: http://localhost:5000/player

## How to play

| Step | Who | Action |
|------|-----|--------|
| 1 | Host | Click **Start New Round** |
| 2 | Host (admin) | `!start_survey` in Discord |
| 3 | Players | `!a <answer>` (max 3 each) |
| 4 | Host (admin) | `!end_survey` |
| 5 | Host | Click **Begin Play** |
| 6 | Host | Select active team → click **Reveal** |
| 7 | Host | Wrong guess → **Add Strike** (3 strikes = lose turn) |
| 8 | Host | **End Round** → **Reset Game** or start new round |

## Discord commands

### Player commands (anyone)

| Command | Description |
|---------|-------------|
| `!a <answer>` | Submit an answer (max 3 per survey) |
| `!my` | See how many submissions you have left |
| `!join` | Request to be assigned to a team |
| `!leave` | Leave your current team |
| `!teams` | Show current team rosters |

### Admin commands (require administrator permission)

| Command | Description |
|---------|-------------|
| `!start_survey` | Open the survey for answers |
| `!end_survey` | Close survey and send results to the game |
| `!assign_team @user Team 1` | Assign a user to Team 1, Team 2, or Team 3 |
| `!balance_teams` | Auto‑assign all waiting players to balance team sizes |
| `!clear_channel 50` | Delete the last 50 messages (default 100) |

## Customise

- **Teams** – edit `TEAMS` list in `backend/app.py` and `discord_bot/bot.py`
- **Questions** – edit `QUESTIONS` array in `frontend/host.html`
- **Point scaling** – modify `normalize_points()` in `app.py`

## Stop the game

Close the two command windows (Backend and Bot) or press `Ctrl+C` in each.

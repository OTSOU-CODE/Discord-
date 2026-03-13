# 🤖 Discord Bot — Detailed Implementation Plans

> **Bot File:** `Discord-manager.py` (1046 lines)
> **Data Files:** `user_stats.json`, `level_requirements.json`, `temp_channels.json`, `config.json`
> **Stack:** `discord.py`, `easy_pil`, vanilla Python

---

## 1. 🏆 Advanced Level System

### Current State

The bot already tracks `voice_minutes` and `text_minutes` per user in `user_stats.json` and assigns roles via `check_level_up()`.

---

### 1.1 — XP Multipliers (Weekends / Special Events)

**File to modify:** `Discord-manager.py`
**Data file to modify:** `config.json`

**Steps:**

1. Add `"xp_multiplier": 1.0` and `"weekend_multiplier": 2.0` to `config.json`.
2. Create a helper function `get_active_multiplier()` that checks:
   - `datetime.now().weekday() >= 5` → return `weekend_multiplier`
   - Else return `xp_multiplier`
3. In `track_voice_minutes()`, replace `stats["voice_minutes"] += 1` with:
   ```python
   multiplier = get_active_multiplier()
   stats["voice_minutes"] += multiplier
   ```
4. In `on_message()`, apply the same multiplier to `text_minutes` logic.

**New `config.json` keys:**

```json
{
  "xp_multiplier": 1.0,
  "weekend_multiplier": 2.0,
  "special_event_multiplier": 3.0,
  "event_active": false
}
```

---

### 1.2 — Streak Rewards

**New file:** `Data/streaks.json`

**Steps:**

1. Create `streaks.json` to store `{ "user_id": { "last_active_date": "YYYY-MM-DD", "streak": 5 } }`.
2. Create `update_streak(user_id)` function:
   - Called on every `on_message` event.
   - If `last_active_date` was yesterday → increment streak.
   - If today → no change.
   - If older → reset to 1.
3. Create `get_streak_multiplier(streak)`:
   - 1-6 days → `1.0×`, 7-13 days → `1.25×`, 14-29 days → `1.5×`, 30+ days → `2.0×`
4. Apply this multiplier on top of `get_active_multiplier()`.

---

### 1.3 — Level-Up Announcements

**New `config.json` key:** `"levelup_channel_id": 0`

**Steps:**

1. Add a config key for a dedicated level-up announcement channel.
2. In `check_level_up()`, after `await member.add_roles(role)`, send an embed to the announcement channel:
   ```python
   channel = member.guild.get_channel(LEVELUP_CHANNEL_ID)
   embed = discord.Embed(
       title="🎉 Level Up!",
       description=f"{member.mention} reached **Level {real_eligible_level}**!",
       color=discord.Color.gold()
   )
   await channel.send(embed=embed)
   ```
3. Store customizable message templates in `config.json` under `"levelup_message"`.

---

### 1.4 — Tier-Based Role Rewards

**`level_requirements.json` enhancement:**

Add a `"tier"` field per level entry:

```json
"10": { "voice_minutes_required": 100, "text_minutes_required": 50, "role_id": 0, "tier": "bronze" },
"25": { "...", "tier": "silver" },
"50": { "...", "tier": "gold" },
"100": { "...", "tier": "platinum" }
```

In `check_level_up()`:

1. Look up the tier for the current level.
2. Remove old tier roles from the member first.
3. Assign the new tier role (pre-create `Bronze`, `Silver`, `Gold`, `Platinum` roles in the server).

---

### 1.5 — Weekly / Monthly Leaderboards with Auto-Reset

**New file:** `Data/leaderboard.json` — stores weekly/monthly snapshots.

**Steps:**

1. Add a background task `leaderboard_reset_task()`:
   ```python
   while not client.is_closed():
       now = datetime.now()
       if now.weekday() == 0 and now.hour == 0:   # Monday midnight
           await post_leaderboard("weekly")
           reset_weekly_xp()
       if now.day == 1 and now.hour == 0:          # 1st of month
           await post_leaderboard("monthly")
           reset_monthly_xp()
       await asyncio.sleep(3600)   # Check every hour
   ```
2. Track `weekly_voice`, `weekly_text` fields in `user_stats.json`.
3. `post_leaderboard(period)` → sorts users by total XP, posts top 10 embed to a configured channel.
4. Reset fields to `0` after posting.

---

### 1.6 — Milestone Rewards (Levels 100, 200, 500)

**Steps:**

1. Add `"milestone_levels": [100, 200, 500]` to `config.json`.
2. In `check_level_up()`, after role assignment:
   ```python
   if real_eligible_level in MILESTONE_LEVELS:
       await channel.send(embed=milestone_embed(member, real_eligible_level))
       # Award bonus coins (see Economy module)
   ```

---

## 2. 🛡️ Enhanced Moderation

### Current State

The bot has mute-tracking (`check_muted_users`) and basic role checking (`has_admin_role`). No auto-moderation system exists.

---

### 2.1 — New Files

| File                       | Purpose                                               |
| -------------------------- | ----------------------------------------------------- |
| `Data/warnings.json`       | Stores `{ user_id: [{ reason, timestamp, mod_id }] }` |
| `Data/mod_log.json`        | Action history for audit purposes                     |
| `Data/automod_config.json` | Automod rules and thresholds                          |

---

### 2.2 — Warn System with Escalation

**Steps:**

1. Create `warn(member, reason, mod)` function:
   - Appends to `warnings.json`.
   - Counts total warns.
   - Escalates: 1 warn → DM, 3 warns → 10min timeout, 5 warns → 1hr timeout, 7 warns → ban.
2. Add `.warn @user <reason>` text command and `/warn` slash command.
3. Add `.warnings @user` command to list all warnings.
4. Add `.clearwarn @user <index>` to remove a specific warning.

---

### 2.3 — Link & Invite Filtering

**In `on_message()`, before XP tracking:**

```python
BLOCKED_PATTERNS = [
    r"discord\.gg/\w+",           # Invite links
    r"https?://\S+\.(tk|ml|cf)",   # Known phishing TLDs
]
for pattern in BLOCKED_PATTERNS:
    if re.search(pattern, message.content, re.IGNORECASE):
        await message.delete()
        await warn(message.author, "Blocked link/invite", client.user)
        break
```

Add `import re` at the top of the file.
Add a whitelist of allowed domains in `automod_config.json`.

---

### 2.4 — Mention Spam Detection

**New dict:** `mention_tracker = {}` (user_id → list of timestamps)

**Logic in `on_message()`:**

```python
if len(message.mentions) >= 5:
    await message.delete()
    await warn(message.author, "Mention spam", client.user)
```

---

### 2.5 — Message Cooldown Per User

**New dict:** `message_cooldown = {}` (user_id → last_message_timestamp)

```python
COOLDOWN_SECONDS = 2
now = datetime.now()
last = message_cooldown.get(message.author.id)
if last and (now - last).total_seconds() < COOLDOWN_SECONDS:
    await message.delete()
    return
message_cooldown[message.author.id] = now
```

---

### 2.6 — Mod Log with Webhook

**Steps:**

1. Add `"mod_log_webhook_url": ""` to `config.json`.
2. Create `log_mod_action(action, target, mod, reason)`:
   - Appends to `mod_log.json`.
   - POSTs a JSON embed payload to the webhook URL using `aiohttp`.
3. Call this from every moderation action (warn, kick, ban, timeout).

**Requires:** `pip install aiohttp` → add to `requirements.txt`.

---

### 2.7 — Slowmode Presets

**Add to `.slowmode` command:**

```python
PRESETS = {"relaxed": 5, "moderate": 15, "strict": 30}
if args[0] in PRESETS:
    seconds = PRESETS[args[0]]
```

Also expose as `/slowmode <preset>` slash command.

---

## 3. 🎙️ Premium Temp Channels

### Current State

Temp channels are created in `manage_temp_channels()` and tracked in `temp_channels.json`. Owners get permissions via `is_channel_owner()`.

---

### 3.1 — Private / Public Mode

**Currently implemented** via `.lock` / `.unlock`. Enhancement:

1. Store mode in `channel_settings[channel_id]["mode"] = "public"|"private"`.
2. On channel creation, default to `"public"`.
3. Add `/channel mode private|public` slash command.

---

### 3.2 — Channel Cloning

**New command:** `.clone` / `/channel clone`

**Steps:**

1. Read the current channel's settings: `bitrate`, `user_limit`, `overwrites`, `name`.
2. Create a new channel in the same category with identical settings:
   ```python
   cloned = await guild.create_voice_channel(
       name=f"{channel.name} (Clone)",
       category=channel.category,
       bitrate=channel.bitrate,
       user_limit=channel.user_limit,
       overwrites=channel.overwrites
   )
   ```
3. Register the new channel in `temp_channels` with the same owner.

---

### 3.3 — Recording Consent System

**Steps:**

1. Add `"recording": false` to `channel_settings[channel_id]`.
2. When owner enables recording (`.record on`):
   - Send a consent embed to the channel text chat.
   - All members in the channel get a DM asking to consent.
   - Store consents in a dict.
3. If a member does not consent within 60 seconds, move them out of the channel.

---

### 3.4 — Screen Share / Video Permissions Toggle

**New commands:** `.video on|off`, `.screenshare on|off`

**Steps:**

```python
if command == "video":
    enabled = args[0] == "on"
    await channel.set_permissions(
        message.guild.default_role,
        stream=enabled
    )
    await message.reply(f"📹 Video {'enabled' if enabled else 'disabled'}.")
```

---

### 3.5 — Persistent Channel Settings

**Modify `save_temp_channels()`** to also save `channel_settings` to `temp_channels.json`:

```json
{
  "channels": { "channel_id": "owner_id" },
  "settings": {
    "channel_id": {
      "mode": "public",
      "recording": false,
      "video": true
    }
  }
}
```

---

## 4. 💰 Economy & Rewards

### Current State

No economy system exists. This is a full new module.

---

### 4.1 — Coin System

**New file:** `Data/economy.json` — `{ user_id: { "coins": 0, "total_earned": 0 } }`

**New functions:**

```python
def get_coins(user_id) -> int
def add_coins(user_id, amount)
def remove_coins(user_id, amount) -> bool  # Returns False if insufficient
def save_economy()
```

**Coin earning rules (added to existing events):**

- `on_message` → `+1 coin` per unique message minute (same gate as XP)
- `track_voice_minutes` → `+2 coins` per voice minute
- Level-up milestone → `+50 coins`

---

### 4.2 — Daily / Weekly Rewards

**New file:** `Data/economy.json` — add `"last_daily": null`, `"last_weekly": null`

**New commands:** `.daily`, `.weekly`

```python
elif command == "daily":
    econ = get_economy(user_id)
    last = econ.get("last_daily")
    if last and (datetime.now() - datetime.fromisoformat(last)).days < 1:
        await message.reply("⏳ You already claimed your daily reward!")
    else:
        add_coins(user_id, 100)
        econ["last_daily"] = datetime.now().isoformat()
        save_economy()
        await message.reply("✅ Claimed **100 coins** as your daily reward!")
```

---

### 4.3 — Shop System

**New file:** `Data/shop.json` — list of purchasable items:

```json
[
  {
    "id": "channel_rename_token",
    "name": "Channel Rename Token",
    "price": 200,
    "description": "Rename your temp channel for free."
  },
  {
    "id": "xp_boost_24h",
    "name": "24h XP Boost",
    "price": 500,
    "description": "2× XP for 24 hours."
  }
]
```

**New commands:** `.shop` (list items) and `.buy <item_id>`

---

### 4.4 — Minigames

**New commands:**

**Coin Flip:**

```python
elif command == "coinflip":
    bet = int(args[0]) if args else 10
    if not remove_coins(user_id, bet):
        return await message.reply("❌ Insufficient coins.")
    result = random.choice(["heads", "tails"])
    guess = args[1] if len(args) > 1 else "heads"
    if result == guess:
        add_coins(user_id, bet * 2)
        await message.reply(f"🪙 **{result.title()}!** You won **{bet}** coins!")
    else:
        await message.reply(f"🪙 **{result.title()}!** You lost **{bet}** coins.")
```

Add `import random` at top.

**Dice Roll:** Similar pattern, user picks 1-6, roll `random.randint(1,6)`.

---

### 4.5 — Balance & Leaderboard Commands

- `.balance` or `.coins` → show current coin balance, embed format.
- `.richlist` → top 10 richest users embed.

---

## 5. 🔧 Utility Features

### Current State

The bot has `on_member_join` that assigns Level 0 role. No ticket, stats, or poll system exists.

---

### 5.1 — Ticket System

**New file:** `Data/tickets.json` — `{ ticket_id: { "opener_id", "channel_id", "status", "opened_at" } }`

**New `config.json` keys:** `"ticket_category_id": 0`, `"ticket_log_channel_id": 0`

**Steps:**

1. Create `/ticket open` slash command:
   - Creates a private channel under the ticket category.
   - Channel permissions: only the user + staff roles can see it.
   - Sends an embed with a `🔒 Close Ticket` button using `discord.ui.Button`.
2. Create `/ticket close` slash command:
   - Archives the channel (or deletes it).
   - Posts a log embed to the ticket log channel.
3. Ticket ID auto-increments and is stored in `tickets.json`.

---

### 5.2 — Welcome / Leave Messages

**New `config.json` keys:**

```json
"welcome_channel_id": 0,
"leave_channel_id": 0,
"welcome_message": "Welcome {mention} to {server}! You are member #{count}.",
"leave_message": "{name} has left the server."
```

**Modify `on_member_join()`** to send a rich embed:

```python
channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
embed = discord.Embed(
    title="👋 Welcome!",
    description=WELCOME_MESSAGE.format(
        mention=member.mention,
        server=member.guild.name,
        count=member.guild.member_count
    ),
    color=discord.Color.green()
)
embed.set_thumbnail(url=member.display_avatar.url)
await channel.send(embed=embed)
```

Add `@client.event on_member_remove(member)` for leave messages.

---

### 5.3 — Auto-Role Assignment

**New `config.json` key:** `"auto_roles": []` — list of role IDs to assign on join.

**In `on_member_join()`:**

```python
for role_id in AUTO_ROLES:
    role = member.guild.get_role(role_id)
    if role:
        await member.add_roles(role)
```

---

### 5.4 — Reaction Roles

**New file:** `Data/reaction_roles.json` — `{ "message_id": { "emoji": role_id } }`

**Steps:**

1. Admin slash command `/reactionrole add <message_id> <emoji> <role>` — saves to `reaction_roles.json`.
2. Add `@client.event on_raw_reaction_add(payload)`:
   - Look up `payload.message_id` in `reaction_roles.json`.
   - Find the matching emoji → assign the role to `payload.member`.
3. Add `@client.event on_raw_reaction_remove(payload)`:
   - Remove the role from the member.

---

### 5.5 — Polls

**New command:** `.poll <question> | <option1> | <option2> | ...`

**Steps:**

1. Parse the message content by `|` separator.
2. Build an embed with each option numbered.
3. Add number emoji reactions (1️⃣, 2️⃣, …) to the poll message.
4. Optionally add a `duration` param to auto-close and tally results after N minutes.

---

### 5.6 — Reminders

**New file:** `Data/reminders.json` — list of `{ user_id, remind_at (ISO timestamp), message }`.

**New command:** `.remind <time> <message>` (e.g., `.remind 30m Take a break`)

**Steps:**

1. Parse duration strings: `30m`, `2h`, `1d` → compute `remind_at`.
2. Save to `reminders.json`.
3. Add background task `check_reminders()`:
   - Runs every 60 seconds.
   - For each expired reminder, DMs the user and removes it from the file.

---

## 6. ⚙️ Command Framework Improvements

### Current State

Commands mix text-based (`.command`) and one slash command (`/kick`). No cooldown, no analytics, no aliases.

---

### 6.1 — Migrate All Commands to Slash

**Strategy:** Keep existing `.command` handlers but add `@client.tree.command()` equivalents for every major command.

**Priority order:**

1. `/rank` — most used
2. `/warn`, `/warnings`, `/clearwarn`
3. `/daily`, `/weekly`, `/balance`, `/shop`, `/buy`
4. `/poll`, `/remind`
5. `/ticket open`, `/ticket close`
6. `/channel rename|limit|lock|unlock|clone` (temp channel group)

Use `discord.app_commands.Group` for grouped commands:

```python
channel_group = discord.app_commands.Group(name="channel", description="Manage your temp channel")

@channel_group.command(name="rename")
async def channel_rename(interaction, name: str): ...

client.tree.add_command(channel_group)
```

---

### 6.2 — Command Cooldowns

**Global cooldown dict:** `command_cooldowns = {}` — `{ (user_id, command): last_used_timestamp }`

**Helper function:**

```python
def check_cooldown(user_id, command, seconds) -> float:
    """Returns remaining seconds if on cooldown, 0 if OK."""
    key = (user_id, command)
    last = command_cooldowns.get(key)
    if last:
        elapsed = (datetime.now() - last).total_seconds()
        if elapsed < seconds:
            return seconds - elapsed
    command_cooldowns[key] = datetime.now()
    return 0
```

**Apply per command:**

```python
remaining = check_cooldown(user_id, "daily", 86400)  # 24h
if remaining > 0:
    await message.reply(f"⏳ On cooldown. Try again in {int(remaining)}s.")
    return
```

---

### 6.3 — Permission Hierarchy

**Define `PermissionLevel` enum:**

```python
from enum import IntEnum
class PermLevel(IntEnum):
    MEMBER = 0
    MODERATOR = 1
    ADMIN = 2
    OWNER = 3
```

**Create `get_perm_level(member)` function:**

```python
def get_perm_level(member):
    if member.id == member.guild.owner_id:
        return PermLevel.OWNER
    if member.guild_permissions.administrator:
        return PermLevel.ADMIN
    # Check for mod role ID from config
    if config.get("mod_role_id") in [r.id for r in member.roles]:
        return PermLevel.MODERATOR
    return PermLevel.MEMBER
```

Apply as a decorator/guard before any sensitive command.

---

### 6.4 — Command Aliases

**In `on_message()`, replace:**

```python
if cmd in [".rank", ".stats", "!rank", "!stats"]:
```

Extend to a centralized alias map:

```python
ALIASES = {
    "rank": ["rank", "stats", "level", "xp"],
    "daily": ["daily", "claim"],
    "balance": ["balance", "bal", "coins", "wallet"],
}
```

Parse `cmd.lstrip(".!")` and check against all alias lists.

---

### 6.5 — Command Usage Analytics

**New file:** `Data/analytics.json` — `{ command_name: { "total": 0, "hourly": {} } }`

**Create `log_command(command_name)` function:**

```python
def log_command(command_name):
    analytics = load_analytics()
    hour_key = datetime.now().strftime("%Y-%m-%d %H")
    if command_name not in analytics:
        analytics[command_name] = {"total": 0, "hourly": {}}
    analytics[command_name]["total"] += 1
    analytics[command_name]["hourly"][hour_key] = analytics[command_name]["hourly"].get(hour_key, 0) + 1
    save_analytics(analytics)
```

Call `log_command(command)` at the start of every command handler.

**Admin command:** `/analytics` — shows top 10 commands by usage as an embed.

---

## 📦 New Files Summary

| File                       | Purpose                        |
| -------------------------- | ------------------------------ |
| `Data/streaks.json`        | Daily streak tracking          |
| `Data/economy.json`        | Coins, daily/weekly timestamps |
| `Data/shop.json`           | Shop item catalog              |
| `Data/tickets.json`        | Support ticket registry        |
| `Data/reminders.json`      | Scheduled user reminders       |
| `Data/warnings.json`       | Per-user warning history       |
| `Data/mod_log.json`        | Moderation action audit log    |
| `Data/analytics.json`      | Command usage statistics       |
| `Data/reaction_roles.json` | Emoji → Role mappings          |
| `Data/leaderboard.json`    | Weekly/monthly XP snapshots    |
| `Data/automod_config.json` | Automod rules and thresholds   |

## 📦 New Config Keys Summary

```json
{
  "creator_channel_id": 0,
  "temp_channel_category_id": 0,
  "xp_multiplier": 1.0,
  "weekend_multiplier": 2.0,
  "special_event_multiplier": 3.0,
  "event_active": false,
  "levelup_channel_id": 0,
  "levelup_message": "🎉 {mention} reached Level {level}!",
  "milestone_levels": [100, 200, 500],
  "mod_log_webhook_url": "",
  "mod_role_id": 0,
  "ticket_category_id": 0,
  "ticket_log_channel_id": 0,
  "welcome_channel_id": 0,
  "leave_channel_id": 0,
  "welcome_message": "Welcome {mention} to {server}! You are member #{count}.",
  "leave_message": "{name} has left the server.",
  "auto_roles": []
}
```

## 📦 New pip Dependencies

```txt
aiohttp       # Mod-log webhooks
```

Add to `requirements.txt`.

---

_Last Updated: 2026-02-28_

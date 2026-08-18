# BWC OnboardingBot

OnboardingBot is the Black Widow Company Discord onboarding bot. It is a Discord-only stop-gap onboarding system intended to handle new-user gating, game-role assignment, Star Citizen RSI profile collection, private command-team notification, and MIMIC screening until a later OAuth2/forum/OpServ onboarding system replaces it.

The current bot does **not** create forum accounts, does **not** use OAuth2, and does **not** submit formal recruitment applications. It helps route new Discord users into the correct access roles and notifies the appropriate game command staff for follow-up.

---

## Current Production Functionality

OnboardingBot currently supports:

- Rules acknowledgement
- SOP acknowledgement, with help request handling
- Guest-only onboarding
- Primary game selection
- Optional additional/secondary game selection
- Guest + game-role assignment
- Onboarding audit logging
- Primary-game command-team notification
- Star Citizen RSI Citizen profile URL collection
- RSI Citizen URL locale normalization
- MIMIC lookup for Star Citizen applicants
- Private Star Citizen C&S alerting for RSI/MIMIC results
- Staff outreach tracking with an **I have reached out** button

Supported games are currently:

- Dune
- MechWarrior Online
- Star Citizen
- Vanguard

---

## User Onboarding Flow

A new Discord user clicks the **Start Onboarding** button and proceeds through the following flow:

1. Confirm they have read the server rules.
2. Confirm they understand the SOP reference.
3. Choose whether they are joining to play a game or are just looking as a guest.
4. If joining to play, choose one primary game.
5. Optionally choose additional games.
6. If Star Citizen is selected as either primary or secondary, enter an RSI Citizen profile URL.
7. Receive the Guest role and selected game roles.
8. The bot posts the relevant audit and command notifications.

The bot treats the selected primary game as the user's main reason for joining. Additional games are granted access roles but do not determine the primary command-team notification.

---

## Star Citizen RSI Profile Requirement

If the user selects **Star Citizen** as either a primary or additional game, OnboardingBot prompts the user to enter their RSI Citizen profile URL.

Accepted URL formats include localized and non-localized RSI Citizen URLs, such as:

```text
https://robertsspaceindustries.com/citizens/Handle
https://robertsspaceindustries.com/en/citizens/Handle
https://robertsspaceindustries.com/de/citizens/Handle
https://robertsspaceindustries.com/fr/citizens/Handle
https://robertsspaceindustries.com/pt-br/citizens/Handle
https://robertsspaceindustries.com/zh-cn/citizens/Handle
```

The bot normalizes submitted RSI Citizen URLs to a consistent English-format URL before adding it to the private Star Citizen command alert.

The RSI URL is **not** included in the general onboarding-log audit message. It is only included in the relevant private command-team alert.

---

## MIMIC Intel Check

When Star Citizen is selected and an RSI Citizen profile is submitted, OnboardingBot runs a read-only MIMIC check.

The MIMIC check may include:

- Direct RSI handle match
- Alias match
- Player watchlist match
- Known MIMIC primary org match
- Current visible RSI main organization match
- Org watchlist match
- Recent report history
- Associated reported orgs
- Recent report references

The MIMIC check does **not** block onboarding. The user still completes onboarding and receives the appropriate roles unless normal role assignment fails.

MIMIC results are shown only in the private Star Citizen command alert.

Possible MIMIC statuses include:

```text
✅ CLEAR
No active player/org watchlist hit or recent report history found.

⚠️ REVIEW
Some report history, uncertain match, inactive/historical watch, or moderate signal.

🚨 HOLD / ESCALATE
Active high/critical player watchlist, active high/critical org watchlist, or high computed risk.

⚠️ MIMIC CHECK UNAVAILABLE
The database or profile check could not be completed. Manual S-2 review is recommended.

⚪ MIMIC CHECK NOT CONFIGURED
MIMIC lookup is disabled for this OnboardingBot instance.
```

---

## Command-Team Notification Behavior

When onboarding completes successfully for a game user, the bot posts the normal onboarding audit embed to the onboarding/join-log channel.

If the user selected a primary game with a configured command channel, the bot also posts a private command-team alert for that primary game.

Example:

```text
Primary Game: Star Citizen
Additional Games: MechWarrior Online, Dune
```

Expected behavior:

- The onboarding-log channel receives the normal onboarding audit.
- The Star Citizen command channel receives a private command-team alert.
- The Star Citizen C&S role is pinged if configured.
- MechWarrior Online and Dune command channels are not pinged because they were secondary selections.

If Star Citizen is selected as a secondary game while another game is primary, the bot can still send the Star Citizen-specific RSI/MIMIC alert to the configured Star Citizen command channel.

---

## Command-Team Alert Buttons

Private command-team alerts include staff action buttons.

### Open member profile / DM

This is a Discord profile URL button for the onboarded member. Discord bots cannot force-open a DM conversation through the API, so this button opens the member profile page:

```text
https://discord.com/users/<USER_ID>
```

Staff can use that profile to message the user.

### I have reached out

This button marks the command alert as resolved. Pressing it updates the embed to show that a staff member has reached out and disables the resolution button.

Use this button only after command staff have contacted the member or otherwise taken ownership of follow-up.

---

## C&S Staff Guide

For game company leadership / C&S staff:

1. Watch your private command chat for OnboardingBot alerts.
2. If your game is the user's primary game, your command chat receives the main follow-up alert.
3. Review the user's primary game, additional games, Discord ID, and action-needed text.
4. For Star Citizen applicants, review the RSI Citizen profile and MIMIC Intel Check.
5. Use **Open member profile / DM** to contact the user.
6. Help the user begin the formal recruitment/application process and get them scheduled for an Op or next appropriate step.
7. Click **I have reached out** only after someone has contacted or taken ownership of the user.

The onboarding-log audit is for general visibility. The private command alert is the actionable leadership follow-up item.

---

## Technical Overview

OnboardingBot is a Python Discord bot using `discord.py`.

Core runtime files:

```text
bot.py
config.py
utils.py
requirements.txt
Dockerfile
cogs/onboarding.py
services/__init__.py
services/mimic_lookup.py
```

The bot expects configuration through environment variables. In Docker production, these should be injected into the container by the deployment environment. A local `.env` file may be used for development, but real `.env` files should not be committed to GitHub.

---

## Dependencies

The current runtime requirements are:

```text
discord.py==2.6.4
python-dotenv==1.2.1
PyMySQL>=1.1.1
```

`PyMySQL` is required for the read-only MIMIC database lookup.

The RSI profile scrape uses Python standard library modules and does not require `requests`, `beautifulsoup4`, or `aiohttp` beyond what `discord.py` already installs.

---

## Docker Deployment

The bot is intended to be deployed as a Docker container.

Recommended Docker behavior:

1. Use a Python 3.12 slim base image.
2. Copy `requirements.txt`.
3. Install Python dependencies.
4. Copy the bot code.
5. Run `python bot.py`.
6. Inject all production variables at container runtime.

Recommended Dockerfile:

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m botuser
USER botuser

CMD ["python", "bot.py"]
```

The code can still call `load_dotenv()`. If no `.env` file exists inside the container, the bot will use the environment variables provided by Docker.

---

## Required Discord Permissions

The bot should be installed as a **Guild Install** application.

Recommended OAuth2 scopes:

```text
bot
applications.commands
```

Required bot permissions:

```text
View Channels
Send Messages
Embed Links
Read Message History
Manage Roles
Use External Emojis
```

Optional permission:

```text
Mention @everyone, @here, and All Roles
```

The optional mention permission is only needed if configured staff roles are not otherwise mentionable. Prefer making only the specific staff roles mentionable instead of giving broad mention permissions.

The bot's role must be above every role it needs to assign:

```text
Guest
Dune
MechWarrior Online
Star Citizen
Vanguard
```

If the bot has `Manage Roles` but its role is below the target roles, role assignment will fail.

---

## Discord Developer Portal Intents

Enable these privileged intents for the bot application:

```text
Server Members Intent
Message Content Intent
```

The Members intent is needed for role checks and role assignment.

The current bot uses Message Content intent because it checks recent channel history for an existing Start Onboarding message. A future version could remove this requirement by storing a start message ID or using an admin command to post the onboarding panel.

---

## Environment Variables

A separate deployment variables document should contain the full variable list with empty values for production configuration.

The major categories are:

```text
General bot settings
Discord channel IDs
Discord role IDs
Game access roles
Game staff/C&S ping roles
Game command-channel IDs
SOP and ASOP URLs
MIMIC database settings
MIMIC timeout/scan settings
```

The production container must receive these values at runtime.

Do not bake real Discord tokens, database passwords, or production IDs directly into the Docker image.

---

## MIMIC Database Access

OnboardingBot only needs read access to the MIMIC database.

Use a MySQL account that can perform `SELECT` queries against the required MIMIC tables. It does not need write access.

The bot currently checks MIMIC with the values supplied through:

```text
MIMIC_DB_ENABLED
MIMIC_DB_HOST
MIMIC_DB_PORT
MIMIC_DB_NAME
MIMIC_DB_USER
MIMIC_DB_PASSWORD
```

Recommended default scan/timing values:

```text
MIMIC_RECRUIT_SCAN_DAYS=180
MIMIC_RSI_PROFILE_SCRAPE_ENABLED=true
MIMIC_RSI_HTTP_TIMEOUT_SECONDS=15
MIMIC_DB_CONNECT_TIMEOUT_SECONDS=8
MIMIC_DB_READ_TIMEOUT_SECONDS=10
```

`MIMIC_RECRUIT_SCAN_DAYS` controls how far back the bot looks when summarizing recent report history for the submitted RSI handle.

---

## Runtime Channels

The bot uses several channel categories:

### Start Channel

Where the Start Onboarding button is posted.

### Onboarding / Join Logs Channel

Where completed onboarding audit embeds are posted.

### SOP Help Channel

Where the bot posts a help request if a user clicks **No / I need help** on the SOP step.

### Game Command Channels

Private command chats for game leadership. These receive primary-game follow-up alerts.

Examples:

```text
Dune command channel
MWO command channel
Star Citizen command channel
Vanguard command channel
```

Star Citizen command alerts also include RSI profile and MIMIC information when applicable.

---

## Runtime Roles

The bot uses several role categories:

### Guest Role

Baseline role assigned to onboarded users.

### Game Access Roles

Roles assigned based on primary and secondary game selections.

### Staff / C&S Ping Roles

Roles pinged in onboarding logs and/or private command-channel alerts.

Only the primary game's C&S role should be pinged for the main command-team follow-up alert.

---

## Expected Production Deployment Steps

For the tech officer:

1. Confirm the GitHub repository contains the latest stable code.
2. Confirm `requirements.txt` includes `discord.py`, `python-dotenv`, and `PyMySQL`.
3. Build the Docker image from the repository.
4. Configure all production environment variables outside the image.
5. Invite/install the production bot in the BWC Discord as a Guild Install.
6. Enable required Developer Portal intents.
7. Confirm the bot role is above all assignable roles.
8. Confirm the bot can view/send/embed in all required channels.
9. Run the container.
10. Watch startup logs for successful extension load and environment label.
11. Test one guest path and one Star Citizen path before announcing production readiness.

Expected successful startup log pattern:

```text
Loaded extension: cogs.onboarding
Logged in as OnboardingBot...
Running environment: PROD
Registered persistent onboarding start view for PROD.
```

---

## Troubleshooting

### Bot starts but does not post the Start Onboarding panel

Check:

```text
START_CHANNEL_ID
bot channel permissions
Read Message History permission
Send Messages permission
Message Content intent
```

### Bot cannot assign roles

Check:

```text
Manage Roles permission
bot role hierarchy
correct role IDs
server/guild mismatch
```

### SOP help posts to the wrong channel

Check:

```text
SOP_HELP_CHANNEL_ID
bot permission to view/send in that private channel
fallback behavior to JOIN_LOGS_CHANNEL_ID
```

### Command alert does not appear

Check:

```text
COMMAND_CHANNEL_ID_<GAME>
bot permission to view/send in that command channel
primary game selection
successful onboarding completion
```

### Staff role is not pinged

Check:

```text
STAFF_PING_ROLE_ID_<GAME>
role exists in the server
role is mentionable or bot has allowed mention permission
allowed_mentions behavior
```

### RSI URL rejected

Use an RSI Citizen profile URL, not a Spectrum profile, organization page, or moniker-only text.

Accepted examples:

```text
https://robertsspaceindustries.com/en/citizens/Handle
https://robertsspaceindustries.com/citizens/Handle
```

### MIMIC check unavailable

Check:

```text
MIMIC_DB_ENABLED=true
MIMIC_DB_HOST
MIMIC_DB_PORT
MIMIC_DB_NAME
MIMIC_DB_USER
MIMIC_DB_PASSWORD
database network access from the container
PyMySQL installed
```

If MIMIC is unavailable, onboarding should still complete and the command alert should recommend manual S-2 review.

---

## Operational Notes

OnboardingBot is a stop-gap onboarding tool. It does not replace:

- Forum account creation
- OAuth2 identity linking
- Formal recruitment application workflow
- OpServ integration
- Human C&S follow-up
- S-2 review when MIMIC raises concerns

Its job is to make the initial Discord onboarding process safer, clearer, and more useful while handing the right follow-up information to the correct staff teams.

---

## Stable Baseline Summary

This build should be treated as the current stable baseline for the new OnboardingBot:

```text
Discord-only onboarding
Guest/game role assignment
Primary + secondary game selection
Star Citizen RSI profile capture
MIMIC read-only intel check
Onboarding-log audit embed
Private primary-game command alert
C&S outreach resolution button
Docker-ready runtime
Environment-variable based configuration
```

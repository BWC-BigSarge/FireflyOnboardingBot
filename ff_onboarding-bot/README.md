# Quartermaster (Onboarding Bot) 🫡

**Quartermaster** is a specialized Discord bot designed for the **Black Widow Company (BWC)**. It serves as the first point of contact for new recruits, handling the onboarding process, role distribution ("issuing kit"), and access control.

## 📋 Features

*   **Interactive Onboarding Wizard**: A private (ephemeral) multi-step questionnaire (Rules, SOP, Game Selection).
*   **Dynamic "Kit" Issue**: Automatically assigns roles based on user selection:
    *   **Game Roles**: Specific roles for games like Star Citizen, MWO, etc.
    *   **Guest Pass**: A "Guest" role for visitors.
*   **Security & Access Control**:
    *   **Anti-Double Dipping**: Prevents users from running the onboarding wizard if they already have roles.
    *   **Secure Commands**: Limits usage of `!` commands strictly to the Developer.
    *   **Silent Operation**: Ignores unauthorized command attempts completely.
*   **Auditing & Logistics**:
    *   **Rich Logs**: Posts detailed Embeds to a log channel upon onboarding completion.
    *   **Staff Alerts**: Pings the relevant game staff (Game Role) when a new recruit joins their division.
    *   **Error Reporting**: Silently catches errors and reports them to the Developer via DM and the log channel.
*   **Modular Design**: Built with Discord Cogs for easy future expansion (Nicknames, Events).

## 🚀 Deployment

### Option A: Docker (Recommended)

1.  **Build the Container**:
    ```bash
    docker build -t onboarding-bot .
    ```

2.  **Run the Quartermaster**:
    ```bash
    docker run -d \
      --name quartermaster \
      --restart unless-stopped \
      --env-file .env \
      ghcr.io/the-bwc/onboarding-bot:latest
    ```

### Option B: Local Python

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure Environment**:
    Create a `.env` file (see Configuration).
3.  **Run**:
    ```bash
    python bot.py
    ```

## ⚙️ Configuration

The bot is configured via environment variables in a `.env` file.

| Variable | Description |
| :--- | :--- |
| `DISCORD_TOKEN` | **Required.** The Bot User Token. |
| `DEVELOPER_ID` | **Required.** Discord User ID of the maintainer (for DMs/Admin). |
| `START_CHANNEL_ID` | Channel ID where the permanent "Start Onboarding" button lives. |
| `JOIN_LOGS_CHANNEL_ID` | Channel ID for audit logs. |
| `GUEST_ROLE_ID` | Role ID assigned to Guests. |
| `ROLE_ID_STAR_CITIZEN` | Role ID for Star Citizen. |
| `ROLE_ID_MWO` | Role ID for MechWarrior Online. |
| `ROLE_ID_...` | See `config.py` for all game overrides. |

### Adding New Games
Edit `config.py` to add new entries to the `GAME_ROLES` dictionary. Each entry needs a display label, a Role ID source (env var), and an emoji.

## 📂 Project Structure

```text
/
├── bot.py                # Main Runner / Cog Loader
├── config.py             # Configuration / Env Var Parsing
├── utils.py              # Shared Utilities (Logging)
├── cogs/
│   └── onboarding.py     # Main Logic (Wizard, Views, Roles)
└── docs/                 # Documentation (Walkthroughs, Plans)
    └── bot_walkthrough.md
```

## 🔒 Permissions

The bot requires the following permissions to function:
*   **Manage Roles** (Must be hierarchically superior to Game Roles)
*   **View Channels** & **Send Messages** (Start/Log Channels)
*   **Embed Links**
*   **Privileged Intents**: `Server Members` and `Message Content`.

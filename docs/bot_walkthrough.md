# Discord Onboarding Bot Walkthrough

The **Onboarding Bot** is now fully operational! It welcomes new users, prompts them with a "Start Onboarding" button, handles role assignment based on game selection, and provides robust error handling.

## 📂 Project Structure
```text
project_root/
├── bot.py                # Main runner (loads Cogs)
├── config.py             # Configuration
├── utils.py              # Shared utilities (Log Error)
├── cogs/                 # Modular features
│   └── onboarding.py     # Onboarding Wizard logic
└── .env                  # Secrets
```

## 🔒 Permissions & Intents
To function without "Administrator" rights, the bot (Quartermaster) requires the following:

### Bot Permissions
*   **Manage Roles**: To assign Guest/Game roles.
    *   *Note*: The Bot's own role must be **higher** in the server hierarchy than the roles it is assigning on `Server Settings > Roles`.
*   **View Channels**: To see the Start and Log channels.
*   **Send Messages**: To post the Start Button and Logs.
*   **Embed Links**: To send formatted Log Embeds.
*   **Read Message History**: To check if the "Start Onboarding" button is already posted on startup.

### Privileged Intents (Developer Portal)
You must enable these toggles in the Discord Developer Portal under **Bot > Privileged Gateway Intents**:
*   **Server Members Intent**: To read user roles to prevent re-onboarding.
*   **Message Content Intent**: To read channel history (to find the existing Start button).

## 🚀 How to Run

1.  **Activate Virtual Environment:**
    ```bash
    source venv/bin/activate
    ```
2.  **Start the Bot:**
    ```bash
    python bot.py
    ```

3.  **Run with Docker:**
    ```bash
    # Build the image
    docker build -t onboarding-bot .

    # Run the container (Mounting .env)
    docker run -d --name onboarding-bot --env-file .env onboarding-bot
    ```

## ⚙️ Configuration

The bot is designed to be easily configurable via `config.py` and `.env`.

### adding New Games
To add a new game to the dropdown menu:
1.  Open `config.py`.
2.  Add a new entry to the `GAME_ROLES` dictionary.
    ```python
    GAME_ROLES = {
        # ... existing games ...
        "New Game Name": {"role_id": 123456789, "emoji": "🎮"},
    }
    ```
    *   **Role ID:** Right-click the role in Discord Settings > Copy ID (Developer Mode must be on).
    *   **Emoji:** Can be a standard unicode emoji (`🚀`) or a custom ID (`<:name:123456789>`).

### Environment Variables (.env)
*   `DISCORD_TOKEN`: Your Bot Token.
*   `Start_CHANNEL_ID`: Channel where the "Start" button lives.
*   `JOIN_LOGS_CHANNEL_ID`: Channel where logs are sent.
*   `GUEST_ROLE_ID`: ID for the Guest role.
*   `ROLE_ID_STAR_CITIZEN`, `ROLE_ID_MWO`, etc.: IDs for specific game roles.

## 🛡️ Error Handling

The bot logs errors in two ways:
1.  **Channel Log**: A Red Embed in the `join-logs` channel with context (User, Location, Traceback).
2.  **Developer DM**: A direct message to the configured `DEVELOPER_ID`.

### User Feedback
If an error occurs during onboarding (e.g., Role not found):
*   The User gets a warning message: *"⚠️ Attention Needed... Your onboarding info was saved, but we encountered an issue..."*
*   The Log Embed is titled **"⚠️ Onboarding Incomplete"** and colored **Orange**.

## 🧩 Adding New Features (Cogs)
The bot uses a modular **Cogs** system. To add a new feature (e.g., Nicknames):
1.  Create a new file `cogs/nicknames.py`.
2.  Define a class inheriting from `commands.Cog`.
3.  Add `async def setup(bot):` to load it.
4.  In `bot.py`, add `'cogs.nicknames'` to the `initial_extensions` list.

## 📸 Usage Flow
1.  User clicks **"Start Onboarding"**.
2.  Selects **"Yes"** for Rules.
3.  Selects **"Yes"** for SOP.
4.  Chooses **"To Play"** or **"Guest"**.
5.  If "To Play", selects a **Game** from the dropdown.
6.  Bot assigns role and logs the result.

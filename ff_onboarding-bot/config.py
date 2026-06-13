import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration Instructions ---
# 1. Production values are hardcoded as defaults below.
# 2. To use Development settings, set the specific environment variables in .env
#    (e.g., START_CHANNEL_ID=12345)
# ----------------------------------

# Secrets (Must be in .env)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# User IDs
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", 299192199843676171))

# Channel IDs / Names
# Default to Production ID (482634171961966613) provided by user
START_CHANNEL_ID = int(os.getenv("START_CHANNEL_ID", 482634171961966613))

# Default to "join-logs" channel ID, can be overridden for dev
JOIN_LOGS_CHANNEL_ID = int(os.getenv("JOIN_LOGS_CHANNEL_ID", 1462542309278224527))

# Rules/SOP references
RULES_CHANNEL_ID = int(os.getenv("RULES_CHANNEL_ID", 480367647150833674))
SOP_URL = os.getenv("SOP_URL", "http://the-bwc.com/forum/index.php?pages/SOP/")

# Guest Role ID
GUEST_ROLE_ID = int(os.getenv("GUEST_ROLE_ID", 480386348507987968))


# Game Roles Configuration
# Format: "Label": {"role_id": 123456789, "emoji": "Emoji"}
# Emoji can be:
#   1. A standard unicode emoji (e.g., "🚀")
#   2. A custom server emoji ID string (e.g., "<:pepe:123456789123456789>")
GAME_ROLES = {
    "Dune": {
        "role_id": int(os.getenv("ROLE_ID_DUNE", 1408950061433618573)),
        "emoji": ":DUNE:1408956336137441350",
        "description": "Dune game-channel access",
        "notes": "You are requesting Dune access. Follow BWC rules, comms discipline, and any Dune-specific guidance posted by leadership.",
        "asop_url": os.getenv("ASOP_URL_DUNE", ""),
        "staff_ping_role_id": int(os.getenv("STAFF_PING_ROLE_ID_DUNE", 0)) or None,
    },
    "Mechwarrior Online": {
        "role_id": int(os.getenv("ROLE_ID_MWO", 480372104160608267)),
        "emoji": ":MWO:844570348677759066",
        "description": "MWO game-channel access",
        "notes": "You are requesting MechWarrior Online access. Follow BWC rules, comms discipline, and any MWO-specific guidance posted by leadership.",
        "asop_url": os.getenv("ASOP_URL_MWO", ""),
        "staff_ping_role_id": int(os.getenv("STAFF_PING_ROLE_ID_MWO", 0)) or None,
    },
    "Star Citizen": {
        "role_id": int(os.getenv("ROLE_ID_STAR_CITIZEN", 480372006806618114)),
        "emoji": ":SC:844564383711494144",
        "description": "Star Citizen game-channel access",
        "notes": "You are requesting Star Citizen access. Use your RSI Handle, not your Moniker, whenever BWC staff asks for RSI identity information.",
        "asop_url": os.getenv("ASOP_URL_STAR_CITIZEN", ""),
        "staff_ping_role_id": int(os.getenv("STAFF_PING_ROLE_ID_STAR_CITIZEN", 0)) or None,
    },
    "Vanguard": {
        "role_id": int(os.getenv("ROLE_ID_VANGUARD", 1437220136799965255)),
        "emoji": ":Vanguard:1437208008395460668",
        "description": "Vanguard game-channel access",
        "notes": "You are requesting Vanguard access. Follow BWC rules, comms discipline, and any Vanguard-specific guidance posted by leadership.",
        "asop_url": os.getenv("ASOP_URL_VANGUARD", ""),
        "staff_ping_role_id": int(os.getenv("STAFF_PING_ROLE_ID_VANGUARD", 0)) or None,
    },
}

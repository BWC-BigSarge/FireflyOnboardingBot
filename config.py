import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration Instructions ---
# All Discord/server-specific IDs must come from environment variables.
# This prevents the DEV test bot from silently falling back to BWC production IDs.
# Use .env.dev for the DEV server and .env.prod for the BWC production server,
# then copy the active one to .env before running.
# ----------------------------------


def required_str(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def required_int(name: str) -> int:
    value = required_str(name)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be a Discord numeric ID, got: {value!r}") from exc


def optional_int(name: str):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be a Discord numeric ID, got: {value!r}") from exc
    return parsed or None


def optional_str(name: str, default: str | None = None):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def optional_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def optional_int_default(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got: {value!r}") from exc


# Environment label used in console output and audit logs.
ENVIRONMENT = os.getenv("ENVIRONMENT", "DEV").strip().upper() or "DEV"

# Secrets
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# User IDs
DEVELOPER_ID = required_int("DEVELOPER_ID")

# Channel IDs
START_CHANNEL_ID = required_int("START_CHANNEL_ID")
JOIN_LOGS_CHANNEL_ID = required_int("JOIN_LOGS_CHANNEL_ID")

# Rules/SOP references
RULES_CHANNEL_ID = required_int("RULES_CHANNEL_ID")
SOP_URL = os.getenv("SOP_URL", "http://the-bwc.com/forum/index.php?pages/SOP/").strip()

# Optional private channel where staff help requests are posted when a user clicks "No / I need help" on the SOP step.
# If not set, the bot falls back to JOIN_LOGS_CHANNEL_ID for backwards compatibility.
SOP_HELP_CHANNEL_ID = optional_int("SOP_HELP_CHANNEL_ID")

# Optional staff role pinged when a user clicks "No / I need help" on the SOP step.
SOP_HELP_STAFF_ROLE_ID = optional_int("SOP_HELP_STAFF_ROLE_ID")

# Guest Role ID
GUEST_ROLE_ID = required_int("GUEST_ROLE_ID")


# Optional MIMIC database integration for Star Citizen recruit checks.
# Uses read-only lookups against MIMIC tables; leave MIMIC_DB_ENABLED false/blank to disable.
MIMIC_DB_ENABLED = optional_bool("MIMIC_DB_ENABLED", False)
MIMIC_DB_HOST = optional_str("MIMIC_DB_HOST", optional_str("DB_HOST"))
MIMIC_DB_PORT = optional_int_default("MIMIC_DB_PORT", optional_int_default("DB_PORT", 3306))
MIMIC_DB_NAME = optional_str("MIMIC_DB_NAME", optional_str("DB_NAME"))
MIMIC_DB_USER = optional_str("MIMIC_DB_USER", optional_str("DB_USER"))
MIMIC_DB_PASSWORD = optional_str("MIMIC_DB_PASSWORD", optional_str("DB_PASSWORD"))
MIMIC_RECRUIT_SCAN_DAYS = optional_int_default("MIMIC_RECRUIT_SCAN_DAYS", 180)
MIMIC_RSI_PROFILE_SCRAPE_ENABLED = optional_bool("MIMIC_RSI_PROFILE_SCRAPE_ENABLED", True)
MIMIC_RSI_HTTP_TIMEOUT_SECONDS = optional_int_default("MIMIC_RSI_HTTP_TIMEOUT_SECONDS", 15)
MIMIC_DB_CONNECT_TIMEOUT_SECONDS = optional_int_default("MIMIC_DB_CONNECT_TIMEOUT_SECONDS", 8)
MIMIC_DB_READ_TIMEOUT_SECONDS = optional_int_default("MIMIC_DB_READ_TIMEOUT_SECONDS", 10)


# Game Roles Configuration
# role_id: access role assigned to the applicant.
# staff_ping_role_id: optional staff/recruiter role pinged in the audit log and private command alert.
# command_channel_id: optional private command channel where the primary-game leadership alert is posted.
# Emoji can be a standard unicode emoji, <:custom:123>, or old :name:id format.
GAME_ROLES = {
    "Dune": {
        "role_id": required_int("ROLE_ID_DUNE"),
        "emoji": os.getenv("EMOJI_DUNE", ":DUNE:1408956336137441350"),
        "description": "Dune game-channel access",
        "notes": "You are requesting Dune access. Follow BWC rules, comms discipline, and any Dune-specific guidance posted by leadership.",
        "asop_url": os.getenv("ASOP_URL_DUNE", "").strip(),
        "staff_ping_role_id": optional_int("STAFF_PING_ROLE_ID_DUNE"),
        "command_channel_id": optional_int("COMMAND_CHANNEL_ID_DUNE"),
    },
    "Mechwarrior Online": {
        "role_id": required_int("ROLE_ID_MWO"),
        "emoji": os.getenv("EMOJI_MWO", ":MWO:844570348677759066"),
        "description": "MWO game-channel access",
        "notes": "You are requesting MechWarrior Online access. Follow BWC rules, comms discipline, and any MWO-specific guidance posted by leadership.",
        "asop_url": os.getenv("ASOP_URL_MWO", "").strip(),
        "staff_ping_role_id": optional_int("STAFF_PING_ROLE_ID_MWO"),
        "command_channel_id": optional_int("COMMAND_CHANNEL_ID_MWO"),
    },
    "Star Citizen": {
        "role_id": required_int("ROLE_ID_STAR_CITIZEN"),
        "emoji": os.getenv("EMOJI_STAR_CITIZEN", ":SC:844564383711494144"),
        "description": "Star Citizen game-channel access",
        "notes": "You are requesting Star Citizen access. Use your RSI Handle, not your Moniker, whenever BWC staff asks for RSI identity information.",
        "asop_url": os.getenv("ASOP_URL_STAR_CITIZEN", "").strip(),
        "staff_ping_role_id": optional_int("STAFF_PING_ROLE_ID_STAR_CITIZEN"),
        "command_channel_id": optional_int("COMMAND_CHANNEL_ID_STAR_CITIZEN"),
    },
    "Vanguard": {
        "role_id": required_int("ROLE_ID_VANGUARD"),
        "emoji": os.getenv("EMOJI_VANGUARD", ":Vanguard:1437208008395460668"),
        "description": "Vanguard game-channel access",
        "notes": "You are requesting Vanguard access. Follow BWC rules, comms discipline, and any Vanguard-specific guidance posted by leadership.",
        "asop_url": os.getenv("ASOP_URL_VANGUARD", "").strip(),
        "staff_ping_role_id": optional_int("STAFF_PING_ROLE_ID_VANGUARD"),
        "command_channel_id": optional_int("COMMAND_CHANNEL_ID_VANGUARD"),
    },
}

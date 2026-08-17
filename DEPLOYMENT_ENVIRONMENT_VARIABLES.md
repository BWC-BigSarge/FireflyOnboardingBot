# OnboardingBot Deployment Environment Variables
# All Discord IDs must be numeric IDs from the target Discord server.
## Required

# Environment value is either PROD or DEV
ENVIRONMENT=PROD

# Discord bot token for the DEV bot/application. Firefly has this info.
DISCORD_TOKEN=

# Your Discord user ID, used for developer-only commands/error DMs.
DEVELOPER_ID=262620520699265025

# DEV server channel IDs.
START_CHANNEL_ID=482634171961966613
JOIN_LOGS_CHANNEL_ID=1462542309278224527
RULES_CHANNEL_ID=480367647150833674

# DEV server baseline role assigned to onboarded users.
GUEST_ROLE_ID=480386348507987968

# DEV server game access roles assigned to applicants.
ROLE_ID_DUNE=1408950061433618573
ROLE_ID_MWO=480372104160608267
ROLE_ID_STAR_CITIZEN=480372006806618114
ROLE_ID_VANGUARD=1437220136799965255

# Optional DEV staff role pinged when a user clicks “No / I need help” at SOP.
SOP_HELP_CHANNEL_ID=480375579250786305
SOP_HELP_STAFF_ROLE_ID=480370841901858816

# DEV game staff/recruiter roles pinged in onboarding logs.
# Leave blank to disable pings. (but do not leave blank)
STAFF_PING_ROLE_ID_DUNE=1478143706807926784
STAFF_PING_ROLE_ID_MWO=964959629899628544
STAFF_PING_ROLE_ID_STAR_CITIZEN=913453887460098088
STAFF_PING_ROLE_ID_VANGUARD=1405555621066965143

# DEV game staff channels for secondary leadership pings.
COMMAND_CHANNEL_ID_DUNE=1478144419545743570
COMMAND_CHANNEL_ID_MWO=1265486691947249757
COMMAND_CHANNEL_ID_STAR_CITIZEN=913449794201075712
COMMAND_CHANNEL_ID_VANGUARD=1406345800912601099

# StarCitizen-specific RSI Citizen profile URL cross-check with MIMICbot. Firefly has this info.
MIMIC_DB_ENABLED=true
MIMIC_DB_HOST=
MIMIC_DB_PORT=3306
MIMIC_DB_NAME=
MIMIC_DB_USER=
MIMIC_DB_PASSWORD=
MIMIC_RECRUIT_SCAN_DAYS=365
MIMIC_RSI_PROFILE_SCRAPE_ENABLED=true
MIMIC_RSI_HTTP_TIMEOUT_SECONDS=15
MIMIC_DB_CONNECT_TIMEOUT_SECONDS=8
MIMIC_DB_READ_TIMEOUT_SECONDS=10

# Rules/SOP references.
# The SOP URL may require a BWC forum account.
SOP_URL=http://the-bwc.com/forum/index.php?pages/SOP/

# Optional game-specific ASOP URLs shown during game confirmation.
ASOP_URL_DUNE=
ASOP_URL_MWO=
ASOP_URL_STAR_CITIZEN=https://www.blackwidowcompany.com/forum/index.php?threads/bwc-star-citizen-a-sop.7114/
ASOP_URL_VANGUARD=

# Optional emoji overrides.
# Keep blank to use the defaults from config.py.
EMOJI_DUNE=
EMOJI_MWO=
EMOJI_STAR_CITIZEN=
EMOJI_VANGUARD=

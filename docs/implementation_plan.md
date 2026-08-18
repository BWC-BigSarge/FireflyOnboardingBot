# Cogs Refactoring Plan

## Goal
Compartmentalize the bot's functionality using Discord Cogs. This allows for easier maintenance and future expansion (e.g., adding Nickname management or Event handling Cogs).

## Proposed Structure
```text
project_root/
├── bot.py                # Main entry point (loads Cogs)
├── config.py             # Configuration (Keep as is)
├── utils.py              # Shared utilities (logging, error handling)
├── cogs/                 # Directory for Cogs
│   └── onboarding.py     # Onboarding functionality (Views + logic)
└── .env
```

## Changes

### 1. [NEW] `utils.py`
- Move `log_error` function here so it can be imported by Main, Onboarding Cog, and future Cogs.
- Needs imports: `discord`, `traceback`, `config`.

### 2. [NEW] `cogs/onboarding.py`
- Define `class Onboarding(commands.Cog)`.
- Move `OnboardingView` and `StartView` classes here.
- Move `start_button` logic into the `StartView`.
- Listener `on_ready` logic for persistent views should be handled in the Cog's `setup_hook` or `on_ready` listener.
    *   *Note*: Persistent views need to be re-added on bot restart. Standard practice is to add them in `bot.setup_hook` or separate `on_ready` in the Cog. To keep it clean, the Cog can handle the view persistence.

### 3. [MODIFY] `bot.py`
- Remove all onboarding logic and views.
- Remove error handling (if moved to a global Error Handler cog or just imported).
- Add logic to load extensions from `cogs/` directory on startup.
- Keep `on_command_error` or similar global error handling hooks.

## Verification
- Start bot.
- Verify "Start Onboarding" button still works.
- Verify `!trigger_error` still logs correctly (using the new utility).

# Discord Onboarding Bot

- [x] Initial Setup
    - [x] Create `task.md` and `implementation_plan.md` <!-- id: 0 -->
    - [x] Verify environment (Python version, discord.py installation) <!-- id: 1 -->
- [x] Implementation
    - [x] Create `OnboardingView` class (Buttons/Dropdowns) <!-- id: 2 -->
    - [x] Create persistent `StartView` with "Start" button <!-- id: 8 -->
    - [x] Create `config.py` for Prod/Dev environment handling (Refactored to dynamic list) <!-- id: 9 -->
    - [x] Implement robust error handling (Channel Log + Developer DM) <!-- id: 4 -->
    - [x] Add logging configuration <!-- id: 5 -->
    - [x] Ping game staff (C&S) on onboarding <!-- id: 10 -->
    - [x] Block already onboarded users from running the wizard <!-- id: 11 -->

- [x] Refactor to Cogs
    - [x] Create `cogs/` directory and `utils.py` <!-- id: 12 -->
    - [x] Move error handling to `utils.py` <!-- id: 13 -->
    - [x] Move onboarding logic to `cogs/onboarding.py` <!-- id: 14 -->
    - [x] Update `bot.py` to load extensions <!-- id: 15 -->
- [x] Deployment
    - [x] Create `Dockerfile` and `requirements.txt` <!-- id: 17 -->
- [x] Security
    - [x] Restrict commands (`!`) to Developer only <!-- id: 16 -->
- [x] Verification
    - [x] Verify bot startup <!-- id: 6 -->
    - [x] Test command flows (mock or dry run if possible) <!-- id: 7 -->

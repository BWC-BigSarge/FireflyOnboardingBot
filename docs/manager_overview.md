# Discord Onboarding Bot: Simple Overview

## What is it?
It's a helper bot that automatically greets new people when they join our Discord server. It asks them a few simple questions to get them set up with the right permissions, so we don't have to do it manually.

## How it works
1.  **Welcome Button**: New people see a "Start" button in the welcome channel.
2.  **Private Message**: When they click it, the bot shows a temporary message **only they can see** (it doesn't clutter the chat or send a DM).
3.  **Simple Questions**:
    *   "Have you read the rules?" (Must say Yes)
    *   "Do you understand the SOP?" (Must say Yes)
    *   "Reason for joining?" (To Play vs Guest)
    *   "What is your primary game?" (If playing)
4.  **Automatic Setup**:
    *   If they pick a **Game** (like Star Citizen), the bot gives them access to that game's channels.
    *   It also gives them the basic **Guest** access automatically.
5.  **Record Keeping**: The bot posts a little summary in a staff channel so we know who joined and what they picked.

## Why it's useful
*   **Saves Time**: We don't have update roles for every single new person manually.
*   **Easy for Users**: They get access immediately without waiting for a mod.
*   **Reliable**: Everyone answers the same questions, so we know they've agreed to the rules.
*   **Smart**: If something goes wrong (like a missing permission), the bot tells the user nicely and sends a private message to the developer to fix it.

import asyncio
import traceback

import discord
from discord.ext import commands

import config
from utils import log_error

TOKEN = config.DISCORD_TOKEN
DEVELOPER_ID = config.DEVELOPER_ID

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_error(event, *args, **kwargs):
    """Global event error handler."""
    await log_error(traceback.format_exc(), source=f"Event: {event}", bot=bot)


@bot.event
async def on_command_error(ctx, error):
    # Silently ignore CheckFailures (non-devs) and CommandNotFound.
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return
    await log_error(error, source=ctx)


@bot.command()
async def trigger_error(ctx):
    """Developer-only command to test error handling."""
    try:
        raise ValueError("This is a test error for the Developer DM system.")
    except Exception as e:
        await log_error(e, source=ctx)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Running environment: {config.ENVIRONMENT}")


@bot.check
async def global_dev_check(ctx):
    """Only the configured developer can run prefix commands."""
    return ctx.author.id == DEVELOPER_ID


async def main():
    if not TOKEN:
        print("❌ Error: Please set DISCORD_TOKEN in the active .env file.")
        return

    initial_extensions = [
        "cogs.onboarding",
    ]

    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}.", e)

    await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Critical Error: {e}")

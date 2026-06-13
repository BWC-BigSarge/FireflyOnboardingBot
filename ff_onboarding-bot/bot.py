import discord
from discord.ext import commands
import traceback
import asyncio
import config
from utils import log_error

# Load environment variables
TOKEN = config.DISCORD_TOKEN
DEVELOPER_ID = config.DEVELOPER_ID

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Global Error Handler
@bot.event
async def on_error(event, *args, **kwargs):
    await log_error(traceback.format_exc(), source=f"Event: {event}", bot=bot)

@bot.event
async def on_command_error(ctx, error):
    # SILENTLY ignore CheckFailures (Non-devs) and CommandNotFound (e.g. !help if disabled)
    if isinstance(error, (commands.CheckFailure, commands.CommandNotFound)):
        return
    await log_error(error, source=ctx)

@bot.command()
async def trigger_error(ctx):
    """Command to test error handling."""
    try:
        raise ValueError("This is a test error for the Developer DM system.")
    except Exception as e:
        await log_error(e, ctx)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

# Global Check: Only Developer can run commands
@bot.check
async def global_dev_check(ctx):
    # This check applies to ALL commands, including custom ones.
    return ctx.author.id == DEVELOPER_ID

async def main():
    if not TOKEN:
        print("❌ Error: Please set your DISCORD_TOKEN in the .env file.")
        return

    # Load Cogs
    initial_extensions = [
        'cogs.onboarding'
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
        # Handle manual stop cleanly
        pass
    except Exception as e:
        print(f"❌ Critical Error: {e}")

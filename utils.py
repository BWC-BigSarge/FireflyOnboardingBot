import traceback

import discord
from discord.ext import commands

import config


def _format_traceback(error) -> tuple[str, str]:
    """Return (summary, traceback_text) for exceptions or preformatted traceback strings."""
    if isinstance(error, BaseException):
        summary = f"{type(error).__name__}: {error}"
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        return summary, tb

    if isinstance(error, str):
        cleaned = error.strip()
        first_line = cleaned.splitlines()[0] if cleaned else "Unknown string error"
        return first_line[:300], cleaned or "No traceback provided."

    summary = repr(error)
    return summary[:300], str(error)


def _channel_location(channel) -> str:
    if not channel:
        return "DM or unknown channel"
    name = getattr(channel, "name", "Unknown")
    channel_id = getattr(channel, "id", "Unknown")
    return f"Channel: {name} ({channel_id})"


async def log_error(error, source=None, bot=None):
    """Log errors to the join-logs channel and DM the configured developer."""
    error_summary, tb = _format_traceback(error)

    ctx_info = "Unknown Context"
    user = None
    location = "Unknown"

    if isinstance(source, discord.Interaction):
        user = source.user
        location = _channel_location(source.channel)
        custom_id = "N/A"
        if isinstance(source.data, dict):
            custom_id = source.data.get("custom_id", "N/A")
        ctx_info = f"Interaction: {source.type} | ID: {custom_id}"
        bot = bot or source.client
    elif isinstance(source, commands.Context):
        user = source.author
        location = _channel_location(source.channel)
        ctx_info = f"Command: {source.command.name if source.command else 'Unknown'}"
        bot = bot or source.bot
    elif isinstance(source, str):
        ctx_info = source

    print(f"ERROR [{config.ENVIRONMENT}]: {ctx_info} | {error_summary}")

    embed = discord.Embed(
        title=f"⚠️ [{config.ENVIRONMENT}] Bot Error Occurred",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    if user:
        embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)", inline=True)
    embed.add_field(name="Location", value=location, inline=True)
    embed.add_field(name="Context", value=ctx_info, inline=False)
    embed.add_field(name="Error", value=error_summary[:1024], inline=False)

    if len(tb) > 4000:
        tb = tb[:3990] + "..."
    embed.description = f"```py\n{tb}\n```"

    if config.JOIN_LOGS_CHANNEL_ID and bot:
        log_channel = bot.get_channel(config.JOIN_LOGS_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                print(f"FAILED to send log to channel: {e}")
        else:
            print(f"Could not find Log Channel ID: {config.JOIN_LOGS_CHANNEL_ID}")

    if config.DEVELOPER_ID and bot:
        try:
            dev = await bot.fetch_user(config.DEVELOPER_ID)
            if dev:
                await dev.send(content="🚨 **Critical Error**", embed=embed)
        except Exception as e:
            print(f"Failed to DM developer: {e}")

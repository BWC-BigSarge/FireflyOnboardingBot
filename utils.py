import discord
from discord.ext import commands
import traceback
import config

async def log_error(error, source=None, bot=None):
    """Logs errors to the join-logs channel and DMs the developer."""
    
    # Get traceback
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    
    # Build Context String
    ctx_info = "Unknown Context"
    user = None
    location = "Unknown"
    
    if isinstance(source, discord.Interaction):
        user = source.user
        location = f"Channel: {source.channel.name} ({source.channel.id})" if source.channel else "DM"
        ctx_info = f"Interaction: {source.type} | ID: {source.data.get('custom_id', 'N/A')}"
        if not bot: bot = source.client
    elif isinstance(source, commands.Context):
        user = source.author
        location = f"Channel: {source.channel.name} ({source.channel.id})"
        ctx_info = f"Command: {source.command.name if source.command else 'Unknown'}"
        if not bot: bot = source.bot
    elif isinstance(source, str):
        ctx_info = source

    # Console Log
    print(f"ERROR: {ctx_info} | {error}")
    
    # Create Error Embed
    embed = discord.Embed(title="⚠️ Bot Error Occurred", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    if user:
        embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)", inline=True)
    embed.add_field(name="Location", value=location, inline=True)
    embed.add_field(name="Context", value=ctx_info, inline=False)
    
    # Truncate traceback to fit in field (1024 limit) or description (4096)
    if len(tb) > 4000:
        tb = tb[:3990] + "..."
    embed.description = f"```py\n{tb}\n```"

    # 1. Log to Channel
    if config.JOIN_LOGS_CHANNEL_ID and bot:
        log_channel = bot.get_channel(config.JOIN_LOGS_CHANNEL_ID)
        if log_channel:
            try:
                await log_channel.send(embed=embed) 
            except Exception as e:
                print(f"FAILED to send log to channel: {e}")
        else:
            print(f"Could not find Log Channel ID: {config.JOIN_LOGS_CHANNEL_ID}") 
    
    # 2. DM Developer
    if config.DEVELOPER_ID and bot:
        try:
            dev = await bot.fetch_user(config.DEVELOPER_ID)
            if dev:
                await dev.send(content=f"🚨 **Critical Error**", embed=embed)
        except Exception as e:
            print(f"Failed to DM developer: {e}")

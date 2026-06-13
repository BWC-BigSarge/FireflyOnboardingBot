import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import config
from utils import log_error


def _channel_mention(channel_id: int) -> str:
    return f"<#{channel_id}>" if channel_id else "the Rules channel"


def _parse_emoji(value):
    """Return a SelectOption-compatible emoji value, tolerating old :name:id config strings."""
    if not value:
        return None
    if isinstance(value, str) and value.startswith(":") and value.count(":") == 2:
        try:
            name, emoji_id = value.strip(":").split(":")
            return discord.PartialEmoji(name=name, id=int(emoji_id))
        except Exception:
            return value
    if isinstance(value, str) and value.startswith("<") and value.endswith(">"):
        try:
            return discord.PartialEmoji.from_str(value)
        except Exception:
            return value
    return value


class OnboardingView(View):
    def __init__(self, bot):
        super().__init__(timeout=900)
        self.bot = bot
        self.answers = {}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ephemeral views are only visible to the user, but keep this guard for safety."""
        return True

    # Step 1: Rules
    @discord.ui.button(label="Yes, I have read the rules", style=discord.ButtonStyle.green, custom_id="rules_yes")
    async def rules_yes(self, interaction: discord.Interaction, button: Button):
        self.answers["rules"] = "Yes"
        self.clear_items()

        sop_yes = Button(label="Yes, I understand", style=discord.ButtonStyle.green, custom_id="sop_yes")
        sop_yes.callback = self.sop_yes

        sop_no = Button(label="No / I need help", style=discord.ButtonStyle.red, custom_id="sop_no")
        sop_no.callback = self.sop_no

        back = Button(label="Back to Rules", style=discord.ButtonStyle.secondary, custom_id="sop_back_rules")
        back.callback = self.back_to_rules

        self.add_item(sop_yes)
        self.add_item(sop_no)
        self.add_item(back)

        await interaction.response.edit_message(content=self.sop_prompt(), view=self)

    @discord.ui.button(label="No / Show me the rules", style=discord.ButtonStyle.secondary, custom_id="rules_no")
    async def rules_no(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            f"Please read the server rules in {_channel_mention(config.RULES_CHANNEL_ID)} first, then come back and click **Yes, I have read the rules**.",
            ephemeral=True,
        )

    def rules_prompt(self) -> str:
        return (
            "👋 **Welcome to BWC onboarding.**\n\n"
            f"Before you receive server access, please read the server rules in {_channel_mention(config.RULES_CHANNEL_ID)}.\n\n"
            "Click **Yes** only after you have read them. If you cannot find them, click **No / Show me the rules**."
        )

    def sop_prompt(self) -> str:
        return (
            "📘 **Standard Operating Procedures (SOP)**\n\n"
            f"The SOP reference is posted in {_channel_mention(config.RULES_CHANNEL_ID)}.\n"
            f"Full SOP URL: {config.SOP_URL}\n\n"
            "Important: the full SOP page may require a BWC forum account to access. "
            "This Discord-only onboarding cannot create that account or verify forum access.\n\n"
            "Click **Yes** only if you have read and understand the SOP well enough to proceed. "
            "If you cannot access it, do not understand it, or need a forum account/admin help, click **No / I need help**."
        )

    async def back_to_rules(self, interaction: discord.Interaction):
        self.answers.pop("rules", None)
        self.clear_items()

        yes = Button(label="Yes, I have read the rules", style=discord.ButtonStyle.green, custom_id="rules_yes")
        yes.callback = self.rules_yes
        no = Button(label="No / Show me the rules", style=discord.ButtonStyle.secondary, custom_id="rules_no")
        no.callback = self.rules_no
        self.add_item(yes)
        self.add_item(no)

        await interaction.response.edit_message(content=self.rules_prompt(), view=self)

    # Step 2: SOP
    async def sop_yes(self, interaction: discord.Interaction):
        self.answers["sop"] = "Yes"
        self.clear_items()
        self.add_reason_buttons()
        await interaction.response.edit_message(content=self.reason_prompt(), view=self)

    async def sop_no(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"❌ Please review the SOP reference in {_channel_mention(config.RULES_CHANNEL_ID)}. If the forum page requires an account or you cannot access it, ask an admin/moderator for help before proceeding.",
            ephemeral=True,
        )

    def reason_prompt(self) -> str:
        return (
            "🎯 **Reason for Joining**\n\n"
            "Choose **To Play (Game)** if you are here for one of BWC's supported games. "
            "Choose **Just Looking (Guest)** if you only need guest-level access.\n\n"
            "Guests do not receive hidden game-channel access."
        )

    def add_reason_buttons(self):
        btn_game = Button(label="To Play (Game)", style=discord.ButtonStyle.primary, custom_id="reason_game")
        btn_game.callback = self.reason_game

        btn_guest = Button(label="Just Looking (Guest)", style=discord.ButtonStyle.secondary, custom_id="reason_guest")
        btn_guest.callback = self.reason_guest

        back = Button(label="Back to SOP", style=discord.ButtonStyle.secondary, custom_id="reason_back_sop")
        back.callback = self.back_to_sop

        self.add_item(btn_game)
        self.add_item(btn_guest)
        self.add_item(back)

    async def back_to_sop(self, interaction: discord.Interaction):
        self.answers.pop("sop", None)
        self.clear_items()
        sop_yes = Button(label="Yes, I understand", style=discord.ButtonStyle.green, custom_id="sop_yes")
        sop_yes.callback = self.sop_yes
        sop_no = Button(label="No / I need help", style=discord.ButtonStyle.red, custom_id="sop_no")
        sop_no.callback = self.sop_no
        self.add_item(sop_yes)
        self.add_item(sop_no)
        await interaction.response.edit_message(content=self.sop_prompt(), view=self)

    # Step 3: Reason
    async def reason_game(self, interaction: discord.Interaction):
        self.answers["reason"] = "Game"
        self.clear_items()
        self.add_game_select()
        await interaction.response.edit_message(content="🎮 **Primary Game**\n\nWhich game are you here for? Choose your main game for initial access.", view=self)

    async def reason_guest(self, interaction: discord.Interaction):
        self.answers["reason"] = "Guest"
        self.answers["game"] = "None"

        role_error = None
        guest_role = interaction.guild.get_role(config.GUEST_ROLE_ID) if interaction.guild else None
        if guest_role:
            try:
                await interaction.user.add_roles(guest_role, reason="BWC onboarding: guest selection")
            except Exception as e:
                await log_error(e, interaction)
                role_error = "Failed to assign Guest Role. Please contact an Admin."
        else:
            await log_error(ValueError(f"Guest role not found: {config.GUEST_ROLE_ID}"), interaction)
            role_error = "Guest Role configuration error. Please contact an Admin."

        await self.finish_onboarding(interaction, error_msg=role_error)

    def add_game_select(self):
        options = []
        for label, data in config.GAME_ROLES.items():
            options.append(
                discord.SelectOption(
                    label=label,
                    value=label,
                    emoji=_parse_emoji(data.get("emoji")),
                    description=data.get("description", "Select this game for initial access")[:100],
                )
            )

        select = Select(placeholder="Select your primary game...", options=options, custom_id="game_select", min_values=1, max_values=1)
        select.callback = self.game_select
        self.add_item(select)

        back = Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="game_back_reason")
        back.callback = self.back_to_reason
        self.add_item(back)

    async def back_to_reason(self, interaction: discord.Interaction):
        self.answers.pop("reason", None)
        self.answers.pop("game", None)
        self.clear_items()
        self.add_reason_buttons()
        await interaction.response.edit_message(content=self.reason_prompt(), view=self)

    # Step 4: Game Select -> Confirmation
    async def game_select(self, interaction: discord.Interaction):
        game_label = interaction.data["values"][0]  # type: ignore
        self.answers["game"] = game_label
        self.clear_items()

        confirm = Button(label="Confirm and receive access", style=discord.ButtonStyle.green, custom_id="confirm_game")
        confirm.callback = self.confirm_game
        change = Button(label="Change game", style=discord.ButtonStyle.secondary, custom_id="change_game")
        change.callback = self.reason_game
        self.add_item(confirm)
        self.add_item(change)

        await interaction.response.edit_message(content=self.game_confirmation_prompt(game_label), view=self)

    def game_confirmation_prompt(self, game_label: str) -> str:
        data = config.GAME_ROLES.get(game_label, {})
        notes = data.get("notes") or "No game-specific onboarding note is configured yet."
        asop = data.get("asop_url")
        asop_line = f"\nGame ASOP/reference: {asop}" if asop else ""
        return (
            f"🎮 **Confirm Game Access: {game_label}**\n\n"
            f"{notes}{asop_line}\n\n"
            "Click **Confirm and receive access** to receive this game's Discord role. "
            "Click **Change game** if this is not your primary game."
        )

    async def confirm_game(self, interaction: discord.Interaction):
        await self.finish_onboarding(interaction)

    # Finish
    async def finish_onboarding(self, interaction: discord.Interaction, error_msg: str = None):
        self.clear_items()

        game_label = self.answers.get("game")
        role_id = None

        if game_label and game_label != "None" and game_label in config.GAME_ROLES:
            role_id = config.GAME_ROLES[game_label]["role_id"]

        assigned_role = False
        role_name_display = "Guest"
        role = None

        if role_id and not error_msg:
            role = interaction.guild.get_role(role_id) if interaction.guild else None
            guest_role = interaction.guild.get_role(config.GUEST_ROLE_ID) if interaction.guild else None

            if role:
                role_name_display = role.name
                roles_to_add = [role]
                if guest_role:
                    roles_to_add.append(guest_role)
                else:
                    await log_error(ValueError(f"Guest Role ID not found during Game selection: {config.GUEST_ROLE_ID}"), interaction)

                try:
                    await interaction.user.add_roles(*roles_to_add, reason=f"BWC onboarding: {game_label}")
                    assigned_role = True
                except Exception as e:
                    await log_error(e, interaction)
                    error_msg = f"Failed to assign roles (**{role.name}**). Please contact an Admin."
            else:
                await log_error(ValueError(f"Role ID not found: {role_id} (Game: {game_label})"), interaction)
                error_msg = f"Role for **{game_label}** not found on server (ID: {role_id}). Please contact an Admin."

        await self.send_audit_log(interaction, role, error_msg)

        if error_msg:
            final_msg = f"⚠️ **Attention Needed**\nYour onboarding info was saved, but we encountered an issue:\n> {error_msg}\n\nPlease contact a Moderator or Admin for assistance."
        else:
            final_msg = "✅ **You are all set!** Welcome to the server."
            if assigned_role:
                final_msg += f"\nAssigned Role: **{role_name_display}**"
            elif game_label == "None":
                final_msg += "\nAssigned Role: **Guest**"

        await interaction.response.edit_message(content=final_msg, view=None)

    async def send_audit_log(self, interaction: discord.Interaction, role, error_msg: str = None):
        try:
            log_channel = interaction.guild.get_channel(config.JOIN_LOGS_CHANNEL_ID) if interaction.guild else self.bot.get_channel(config.JOIN_LOGS_CHANNEL_ID)
            if not log_channel:
                return

            embed = discord.Embed(
                title="📥 Onboarding Complete" if not error_msg else "⚠️ Onboarding Incomplete",
                color=discord.Color.green() if not error_msg else discord.Color.orange(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="User", value=f"{interaction.user.mention}\n`{interaction.user.name}`", inline=True)
            embed.add_field(name="Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="Reason", value=self.answers.get("reason", "Unknown"), inline=True)
            embed.add_field(name="Game / Role", value=self.answers.get("game", "None"), inline=True)
            embed.add_field(name="Rules Accepted", value=self.answers.get("rules", "No"), inline=True)
            embed.add_field(name="SOP Understood", value=self.answers.get("sop", "No"), inline=True)

            if error_msg:
                embed.add_field(name="⚠️ Error Warning", value=error_msg, inline=False)

            ping_content = None
            game_label = self.answers.get("game")
            if game_label in config.GAME_ROLES:
                staff_ping_role_id = config.GAME_ROLES[game_label].get("staff_ping_role_id")
                if staff_ping_role_id and interaction.guild:
                    staff_role = interaction.guild.get_role(staff_ping_role_id)
                    if staff_role:
                        ping_content = staff_role.mention

            await log_channel.send(content=ping_content, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True if ping_content else False))
        except Exception as e:
            await log_error(e, interaction)


class StartView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Start Onboarding", style=discord.ButtonStyle.primary, custom_id="start_onboarding_btn", emoji="👋")
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if any(role.id == config.GUEST_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message(
                "✅ **You are already onboarded!**\nYou already have the Guest role. If you need to change your game, please ask a Moderator.",
                ephemeral=True,
            )
            return

        view = OnboardingView(self.bot)
        await interaction.response.send_message(view.rules_prompt(), view=view, ephemeral=True)


class OnboardingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(StartView(self.bot))

        if config.START_CHANNEL_ID:
            channel = self.bot.get_channel(config.START_CHANNEL_ID)
            if channel:
                async for msg in channel.history(limit=5):
                    if msg.author == self.bot.user and "start your onboarding" in msg.content.lower():
                        return

                view = StartView(self.bot)
                await channel.send(
                    f"👋 **Welcome to BWC!**\nClick below to start your onboarding process. You will be asked to review {_channel_mention(config.RULES_CHANNEL_ID)}, acknowledge the SOP reference posted there, and choose guest or game access. The full SOP may require a BWC forum account.",
                    view=view,
                )
            else:
                print(f"Could not find start channel with ID {config.START_CHANNEL_ID}")


async def setup(bot):
    await bot.add_cog(OnboardingCog(bot))

import asyncio

import discord
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View
import re
from urllib.parse import unquote, urlparse

import config
from utils import log_error
from services.mimic_lookup import check_rsi_profile


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


def _env_title(title: str) -> str:
    return f"[{config.ENVIRONMENT}] {title}"


def _format_game_list(game_labels) -> str:
    labels = [label for label in game_labels if label]
    return ", ".join(labels) if labels else "None"


STAR_CITIZEN_LABEL = "Star Citizen"


def _looks_like_locale_segment(segment: str) -> bool:
    """Return True for common RSI locale path segments such as en, de, fr, pt-br, or zh-Hans."""
    return bool(re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8}){0,2}", (segment or "").lower()))


def _normalise_rsi_citizen_profile_url(raw_value: str) -> tuple[str | None, str | None]:
    """Validate and normalise an RSI Citizen profile URL.

    Accepted formats:
    - https://robertsspaceindustries.com/citizens/<RSI_HANDLE>
    - https://robertsspaceindustries.com/<locale>/citizens/<RSI_HANDLE>

    Locale-prefixed examples include /en/citizens, /de/citizens, /fr/citizens,
    /pt-br/citizens, /zh-cn/citizens, and similar language/region variants.

    This deliberately rejects organization pages, Spectrum URLs, and moniker-only text.
    """
    value = (raw_value or "").strip()
    if not value:
        return None, "Please enter your full RSI Citizen profile URL."

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, (
            "Please enter the full RSI Citizen profile URL, including `https://`. "
            "Example: `https://robertsspaceindustries.com/en/citizens/YourHandle`"
        )

    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    if hostname != "robertsspaceindustries.com":
        return None, "That does not look like an RSI Citizen profile URL from robertsspaceindustries.com."

    path_parts = [part.strip() for part in parsed.path.split("/") if part.strip()]

    # Accept both older/shared URLs like /citizens/Handle and current/localized
    # URLs like /en/citizens/Handle, /de/citizens/Handle, /pt-br/citizens/Handle, etc.
    citizens_index = None
    if len(path_parts) >= 2 and path_parts[0].lower() == "citizens":
        citizens_index = 0
    elif (
        len(path_parts) >= 3
        and _looks_like_locale_segment(path_parts[0])
        and path_parts[1].lower() == "citizens"
    ):
        citizens_index = 1

    if citizens_index is None:
        return None, (
            "Please use your RSI **Citizen profile** URL, not your Moniker by itself, Spectrum profile, "
            "or organization page. Example: `https://robertsspaceindustries.com/en/citizens/YourHandle`"
        )

    handle_index = citizens_index + 1
    handle = unquote(path_parts[handle_index].strip()) if len(path_parts) > handle_index else ""
    if not handle or any(char.isspace() for char in handle):
        return None, "The RSI handle portion of the Citizen profile URL appears to be invalid."

    return f"https://robertsspaceindustries.com/en/citizens/{handle}", None


def _includes_star_citizen(primary_game, secondary_games) -> bool:
    return primary_game == STAR_CITIZEN_LABEL or STAR_CITIZEN_LABEL in (secondary_games or [])


def _extract_rsi_handle_from_profile_url(profile_url: str) -> str | None:
    parsed = urlparse(profile_url or "")
    path_parts = [part.strip() for part in parsed.path.split("/") if part.strip()]
    for index, part in enumerate(path_parts):
        if part.lower() == "citizens" and len(path_parts) > index + 1:
            return unquote(path_parts[index + 1]).strip() or None
    return None


def _mimic_embed_color(status: str | None) -> discord.Color:
    if status == "critical":
        return discord.Color.red()
    if status in {"warning", "error"}:
        return discord.Color.orange()
    return discord.Color.blue()


class CommandOutreachView(View):
    """Private command-channel follow-up controls for a completed primary-game onboarding.

    The profile button is a URL button, so it opens the member's Discord profile without
    resolving the alert. Only the "I have reached out" button edits the alert as resolved.
    These buttons are runtime-backed; after a bot restart, staff can still act manually from
    the message contents, but the resolution button will no longer be active.
    """

    def __init__(self, member_id: int, primary_game: str):
        super().__init__(timeout=None)
        self.member_id = member_id
        self.primary_game = primary_game
        self.resolve_custom_id = f"command_outreach_resolved:{member_id}"

        self.add_item(
            Button(
                label="Open member profile / DM",
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/users/{member_id}",
            )
        )

        resolved = Button(
            label="I have reached out",
            style=discord.ButtonStyle.green,
            custom_id=self.resolve_custom_id,
        )
        resolved.callback = self.mark_reached_out
        self.add_item(resolved)

    async def mark_reached_out(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0] if interaction.message and interaction.message.embeds else None
        if embed is None:
            embed = discord.Embed(
                title=_env_title("Primary Game Outreach Resolved"),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )

        resolved_at = discord.utils.utcnow()
        status_value = (
            f"✅ Resolved by {interaction.user.mention}\n"
            f"Resolved: <t:{int(resolved_at.timestamp())}:f>"
        )

        status_index = None
        for index, field in enumerate(embed.fields):
            if field.name == "Status":
                status_index = index
                break

        if status_index is None:
            embed.add_field(name="Status", value=status_value, inline=False)
        else:
            embed.set_field_at(status_index, name="Status", value=status_value, inline=False)

        embed.color = discord.Color.green()

        for child in self.children:
            if getattr(child, "custom_id", None) == self.resolve_custom_id:
                child.disabled = True
                child.label = "Outreach resolved"

        await interaction.response.edit_message(embed=embed, view=self)


class RSIProfileModal(Modal):
    """Collects the RSI Citizen profile URL when Star Citizen is selected."""

    def __init__(self, onboarding_view: "OnboardingView"):
        super().__init__(title="Star Citizen RSI Profile")
        self.onboarding_view = onboarding_view
        self.profile_url = TextInput(
            label="RSI Citizen profile URL",
            placeholder="https://robertsspaceindustries.com/en/citizens/YourHandle",
            required=True,
            max_length=250,
            style=discord.TextStyle.short,
        )
        self.add_item(self.profile_url)

    async def on_submit(self, interaction: discord.Interaction):
        normalised_url, error_message = _normalise_rsi_citizen_profile_url(str(self.profile_url.value))
        if error_message:
            await interaction.response.send_message(
                f"❌ {error_message}\n\nPlease click the confirmation button again and enter your RSI Citizen profile URL.",
                ephemeral=True,
            )
            return

        self.onboarding_view.answers["rsi_profile_url"] = normalised_url
        await self.onboarding_view.finish_onboarding(interaction)


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
        await self.handle_rules_yes(interaction)

    @discord.ui.button(label="No / Show me the rules", style=discord.ButtonStyle.secondary, custom_id="rules_no")
    async def rules_no(self, interaction: discord.Interaction, button: Button):
        await self.handle_rules_no(interaction)

    async def handle_rules_yes(self, interaction: discord.Interaction):
        self.answers["rules"] = "Yes"
        self.clear_items()
        self.add_sop_buttons()
        await interaction.response.edit_message(content=self.sop_prompt(), view=self)

    async def handle_rules_no(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Please read the server rules in {_channel_mention(config.RULES_CHANNEL_ID)} first, then come back and click **Yes, I have read the rules**.",
            ephemeral=True,
        )

    async def rules_yes_dynamic(self, interaction: discord.Interaction):
        await self.handle_rules_yes(interaction)

    async def rules_no_dynamic(self, interaction: discord.Interaction):
        await self.handle_rules_no(interaction)

    def add_sop_buttons(self):
        sop_yes = Button(label="Yes, I understand", style=discord.ButtonStyle.green, custom_id="sop_yes")
        sop_yes.callback = self.sop_yes

        sop_no = Button(label="No / I need help", style=discord.ButtonStyle.red, custom_id="sop_no")
        sop_no.callback = self.sop_no

        back = Button(label="Back to Rules", style=discord.ButtonStyle.secondary, custom_id="sop_back_rules")
        back.callback = self.back_to_rules

        self.add_item(sop_yes)
        self.add_item(sop_no)
        self.add_item(back)

    def rules_prompt(self) -> str:
        return (
            "👋 **Welcome to BWC onboarding.**\n\n"
            f"Before you receive server access, please read the server rules in {_channel_mention(config.RULES_CHANNEL_ID)}.\n\n"
            "Click **Yes** only after you have read them. If you cannot find them, click **No / Show me the rules**."
        )

    def sop_prompt(self) -> str:
        return (
            "📘 **Standard Operating Procedures (SOP)**\n\n"
            f"The SOP reference is posted in {_channel_mention(config.RULES_CHANNEL_ID)}.\n\n"
            f"**__Full SOP URL:__** {config.SOP_URL}\n\n"
            "Important: the full SOP page may require a BWC forum account to access. "
            "This Discord-only onboarding cannot create that account or verify forum access.\n\n"
            "Click **Yes** only if you have read and understand the SOP well enough to proceed. "
            "If you cannot access it, do not understand it, or need a forum account/admin help, click **No / I need help**."
        )

    def sop_help_prompt(self) -> str:
        return (
            "🆘 **SOP / Forum Access Help Requested**\n\n"
            "Staff have been notified that you need help with the SOP or forum access. "
            "You can wait for staff, review the Rules channel again, or go back to the SOP step.\n\n"
            f"Rules channel: {_channel_mention(config.RULES_CHANNEL_ID)}\n\n"
            f"**__Full SOP URL:__** {config.SOP_URL}"
        )

    def add_sop_help_buttons(self):
        back_sop = Button(label="Go Back to SOP", style=discord.ButtonStyle.secondary, custom_id="sop_help_back_sop")
        back_sop.callback = self.back_to_sop
        self.add_item(back_sop)

        back_rules = Button(label="Go Back to Rules", style=discord.ButtonStyle.secondary, custom_id="sop_help_back_rules")
        back_rules.callback = self.back_to_rules
        self.add_item(back_rules)

    async def back_to_rules(self, interaction: discord.Interaction):
        self.answers.pop("rules", None)
        self.clear_items()

        yes = Button(label="Yes, I have read the rules", style=discord.ButtonStyle.green, custom_id="rules_yes")
        yes.callback = self.rules_yes_dynamic
        no = Button(label="No / Show me the rules", style=discord.ButtonStyle.secondary, custom_id="rules_no")
        no.callback = self.rules_no_dynamic
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
        self.answers["sop"] = "Help Requested"
        self.clear_items()
        self.add_sop_help_buttons()

        # Acknowledge the button click immediately by editing the onboarding message.
        # The staff alert is sent after this, so a slow/private channel send cannot cause
        # Discord to show "bot did not respond in time" to the user.
        await interaction.response.edit_message(content=self.sop_help_prompt(), view=self)
        await self.send_sop_help_log(interaction)

    async def send_sop_help_log(self, interaction: discord.Interaction):
        try:
            target_channel_id = config.SOP_HELP_CHANNEL_ID or config.JOIN_LOGS_CHANNEL_ID
            log_channel = (
                interaction.guild.get_channel(target_channel_id)
                if interaction.guild
                else self.bot.get_channel(target_channel_id)
            )
            if not log_channel and target_channel_id != config.JOIN_LOGS_CHANNEL_ID:
                log_channel = (
                    interaction.guild.get_channel(config.JOIN_LOGS_CHANNEL_ID)
                    if interaction.guild
                    else self.bot.get_channel(config.JOIN_LOGS_CHANNEL_ID)
                )
            if not log_channel:
                return

            embed = discord.Embed(
                title=_env_title("🆘 SOP / Forum Access Help Needed"),
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="User", value=f"{interaction.user.mention}\n`{interaction.user.name}`", inline=True)
            embed.add_field(name="Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="Environment", value=config.ENVIRONMENT, inline=True)
            embed.add_field(
                name="Issue",
                value=(
                    "User clicked **No / I need help** on the SOP step. "
                    "They may need help finding the SOP, creating/accessing a forum account, or getting clarification before proceeding."
                ),
                inline=False,
            )

            ping_content = None
            if config.SOP_HELP_STAFF_ROLE_ID and interaction.guild:
                staff_role = interaction.guild.get_role(config.SOP_HELP_STAFF_ROLE_ID)
                if staff_role:
                    ping_content = staff_role.mention

            await log_channel.send(
                content=ping_content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True if ping_content else False),
            )
        except Exception as e:
            await log_error(e, interaction)

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

        self.add_sop_buttons()
        await interaction.response.edit_message(content=self.sop_prompt(), view=self)

    # Step 3: Reason
    async def reason_game(self, interaction: discord.Interaction):
        self.answers["reason"] = "Game"
        self.answers.pop("game", None)
        self.answers.pop("secondary_games", None)
        self.answers.pop("rsi_profile_url", None)
        self.answers.pop("rsi_handle", None)
        self.answers.pop("mimic_intel_check", None)
        self.clear_items()
        self.add_game_select()
        await interaction.response.edit_message(
            content="🎮 **Primary Game**\n\nWhich game are you here for? Choose your main game for initial access.",
            view=self,
        )

    async def reason_guest(self, interaction: discord.Interaction):
        self.answers["reason"] = "Guest"
        self.answers["game"] = "None"
        self.answers["secondary_games"] = []

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

        select = Select(
            placeholder="Select your primary game...",
            options=options,
            custom_id="game_select",
            min_values=1,
            max_values=1,
        )
        select.callback = self.game_select
        self.add_item(select)

        back = Button(label="Back", style=discord.ButtonStyle.secondary, custom_id="game_back_reason")
        back.callback = self.back_to_reason
        self.add_item(back)

    async def back_to_reason(self, interaction: discord.Interaction):
        self.answers.pop("reason", None)
        self.answers.pop("game", None)
        self.answers.pop("secondary_games", None)
        self.answers.pop("rsi_profile_url", None)
        self.answers.pop("rsi_handle", None)
        self.answers.pop("mimic_intel_check", None)
        self.clear_items()
        self.add_reason_buttons()
        await interaction.response.edit_message(content=self.reason_prompt(), view=self)

    # Step 4: Primary game select -> Primary confirmation
    async def game_select(self, interaction: discord.Interaction):
        game_label = interaction.data["values"][0]  # type: ignore
        self.answers["game"] = game_label
        self.answers["secondary_games"] = []
        self.answers.pop("rsi_profile_url", None)
        self.answers.pop("rsi_handle", None)
        self.answers.pop("mimic_intel_check", None)
        self.clear_items()

        confirm = Button(label="Confirm primary game", style=discord.ButtonStyle.green, custom_id="confirm_primary_game")
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
        asop_line = f"\n\n**__Game ASOP/reference:__** {asop}" if asop else ""
        return (
            f"🎮 **Confirm Primary Game: {game_label}**\n\n"
            f"{notes}{asop_line}\n\n"
            "Click **Confirm primary game** to set this as your main game. "
            "After that, you can optionally select any other BWC-supported games you also play."
        )

    async def confirm_game(self, interaction: discord.Interaction):
        self.clear_items()
        self.add_secondary_game_controls()
        await interaction.response.edit_message(content=self.secondary_games_prompt(), view=self)

    # Step 5: Optional secondary games
    def secondary_game_options(self):
        primary_game = self.answers.get("game")
        options = []
        for label, data in config.GAME_ROLES.items():
            if label == primary_game:
                continue
            options.append(
                discord.SelectOption(
                    label=label,
                    value=label,
                    emoji=_parse_emoji(data.get("emoji")),
                    description=data.get("description", "Select this additional game")[:100],
                )
            )
        return options

    def secondary_games_prompt(self) -> str:
        primary_game = self.answers.get("game", "your selected primary game")
        return (
            "🎮 **Additional Games**\n\n"
            f"Your primary game is set to **{primary_game}**.\n\n"
            "Are there any other BWC-supported games you also play? "
            "Select any additional games below. After you choose a game or games from the dropdown, "
            "click outside the dropdown menu to close it. The green confirmation button will appear after the dropdown closes.\n\n"
            "If you do not want any additional game access, click **No additional games**. "
            "If your primary game is wrong, click **Change primary game**."
        )

    def secondary_games_confirmation_prompt(self) -> str:
        primary_game = self.answers.get("game", "your selected primary game")
        selected_games = self.answers.get("secondary_games") or []
        return (
            "🎮 **Confirm Additional Games**\n\n"
            f"Your primary game is set to **{primary_game}**.\n\n"
            f"Pending additional games: **{_format_game_list(selected_games)}**\n\n"
            "Click **Add selected additional games** to receive access for those additional games too. "
            "Click **Change additional games** to reopen the dropdown, **No additional games** to clear the selection, "
            "or **Change primary game** to go back and choose a different primary game."
        )

    def add_secondary_game_controls(self):
        """Initial additional-games screen: dropdown plus navigation buttons.

        The green confirmation button is deliberately not shown here because Discord does
        not reliably re-enable an already-rendered disabled button after a dropdown
        selection. Instead, selecting from the dropdown advances to a clean confirmation
        screen with an always-enabled green button.
        """
        options = self.secondary_game_options()

        if options:
            select = Select(
                placeholder="Select any additional games you also play...",
                options=options,
                custom_id="secondary_game_select",
                min_values=1,
                max_values=len(options),
            )
            select.callback = self.secondary_game_select
            self.add_item(select)

        none_btn = Button(label="No additional games", style=discord.ButtonStyle.red, custom_id="no_secondary_games")
        none_btn.callback = self.no_secondary_games
        self.add_item(none_btn)

        change = Button(label="Change primary game", style=discord.ButtonStyle.secondary, custom_id="secondary_change_primary")
        change.callback = self.change_primary_game
        self.add_item(change)

    def add_secondary_confirmation_controls(self):
        add_btn = Button(
            label="Add selected additional games",
            style=discord.ButtonStyle.green,
            custom_id="add_selected_secondary_games",
        )
        add_btn.callback = self.add_selected_secondary_games
        self.add_item(add_btn)

        change_additional = Button(
            label="Change additional games",
            style=discord.ButtonStyle.secondary,
            custom_id="change_secondary_games",
        )
        change_additional.callback = self.show_secondary_game_select
        self.add_item(change_additional)

        none_btn = Button(label="No additional games", style=discord.ButtonStyle.red, custom_id="no_secondary_games")
        none_btn.callback = self.no_secondary_games
        self.add_item(none_btn)

        change_primary = Button(
            label="Change primary game",
            style=discord.ButtonStyle.secondary,
            custom_id="secondary_confirm_change_primary",
        )
        change_primary.callback = self.change_primary_game
        self.add_item(change_primary)

    async def show_secondary_game_select(self, interaction: discord.Interaction):
        self.answers["secondary_games"] = []
        self.answers.pop("rsi_profile_url", None)
        self.answers.pop("rsi_handle", None)
        self.answers.pop("mimic_intel_check", None)
        self.clear_items()
        self.add_secondary_game_controls()
        await interaction.response.edit_message(content=self.secondary_games_prompt(), view=self)

    async def secondary_game_select(self, interaction: discord.Interaction):
        selected = list(interaction.data.get("values", []))  # type: ignore
        primary_game = self.answers.get("game")
        self.answers["secondary_games"] = [
            game for game in selected if game != primary_game and game in config.GAME_ROLES
        ]
        if not _includes_star_citizen(primary_game, self.answers["secondary_games"]):
            self.answers.pop("rsi_profile_url", None)
        self.answers.pop("rsi_handle", None)
        self.answers.pop("mimic_intel_check", None)

        self.clear_items()
        self.add_secondary_confirmation_controls()
        await interaction.response.edit_message(content=self.secondary_games_confirmation_prompt(), view=self)


    def star_citizen_selected(self) -> bool:
        return _includes_star_citizen(self.answers.get("game"), self.answers.get("secondary_games") or [])

    async def maybe_request_rsi_profile(self, interaction: discord.Interaction) -> bool:
        """Open the RSI profile modal if Star Citizen was selected and no URL is stored yet."""
        if self.star_citizen_selected() and not self.answers.get("rsi_profile_url"):
            await interaction.response.send_modal(RSIProfileModal(self))
            return True
        return False

    async def add_selected_secondary_games(self, interaction: discord.Interaction):
        if not self.answers.get("secondary_games"):
            await interaction.response.send_message(
                "Select one or more additional games from the dropdown first, or click **No additional games**.",
                ephemeral=True,
            )
            return
        if await self.maybe_request_rsi_profile(interaction):
            return
        await self.finish_onboarding(interaction)

    async def no_secondary_games(self, interaction: discord.Interaction):
        self.answers["secondary_games"] = []
        if not self.star_citizen_selected():
            self.answers.pop("rsi_profile_url", None)
        self.answers.pop("rsi_handle", None)
        self.answers.pop("mimic_intel_check", None)
        if await self.maybe_request_rsi_profile(interaction):
            return
        await self.finish_onboarding(interaction)

    async def change_primary_game(self, interaction: discord.Interaction):
        self.answers.pop("game", None)
        self.answers.pop("secondary_games", None)
        self.answers.pop("rsi_profile_url", None)
        self.answers.pop("rsi_handle", None)
        self.answers.pop("mimic_intel_check", None)
        await self.reason_game(interaction)



    async def run_mimic_check_if_needed(self):
        """Run the MIMIC check once after RSI profile capture and before private C&S alerts."""
        if not self.star_citizen_selected():
            self.answers.pop("mimic_intel_check", None)
            return
        if self.answers.get("mimic_intel_check"):
            return

        rsi_profile_url = self.answers.get("rsi_profile_url")
        if not rsi_profile_url:
            return

        rsi_handle = _extract_rsi_handle_from_profile_url(rsi_profile_url)
        if not rsi_handle:
            self.answers["mimic_intel_check"] = {
                "status": "error",
                "label": "⚠️ MIMIC CHECK UNAVAILABLE",
                "summary_text": "Could not extract an RSI Handle from the submitted Citizen profile URL. Manual S-2 review recommended.",
            }
            return

        self.answers["rsi_handle"] = rsi_handle
        self.answers["mimic_intel_check"] = await asyncio.to_thread(
            check_rsi_profile,
            rsi_handle=rsi_handle,
            rsi_profile_url=rsi_profile_url,
        )

    def add_mimic_check_field(self, embed: discord.Embed):
        mimic_check = self.answers.get("mimic_intel_check")
        if not mimic_check:
            return

        status = mimic_check.get("status")
        embed.color = _mimic_embed_color(status)
        embed.add_field(
            name="MIMIC Intel Check",
            value=(mimic_check.get("summary_text") or "MIMIC check returned no summary.")[:1024],
            inline=False,
        )

    # Finish
    async def finish_onboarding(self, interaction: discord.Interaction, error_msg: str = None):
        self.clear_items()

        # Acknowledge the button click before role assignment/logging/command alerts.
        # This prevents Discord from showing a timeout if any server/API action is slow.
        if not interaction.response.is_done():
            await interaction.response.defer()

        primary_game = self.answers.get("game")
        secondary_games = self.answers.get("secondary_games") or []
        selected_games = []

        if primary_game and primary_game != "None" and primary_game in config.GAME_ROLES:
            selected_games.append(primary_game)

        for game_label in secondary_games:
            if game_label in config.GAME_ROLES and game_label not in selected_games:
                selected_games.append(game_label)

        assigned_roles_display = []
        role_lookup_errors = []

        if selected_games and not error_msg:
            roles_to_add = []
            seen_role_ids = set()

            guest_role = interaction.guild.get_role(config.GUEST_ROLE_ID) if interaction.guild else None
            if guest_role:
                roles_to_add.append(guest_role)
                seen_role_ids.add(guest_role.id)
                assigned_roles_display.append(guest_role.name)
            else:
                await log_error(ValueError(f"Guest Role ID not found during game selection: {config.GUEST_ROLE_ID}"), interaction)
                role_lookup_errors.append("Guest")

            for game_label in selected_games:
                role_id = config.GAME_ROLES[game_label]["role_id"]
                role = interaction.guild.get_role(role_id) if interaction.guild else None
                if not role:
                    await log_error(ValueError(f"Role ID not found: {role_id} (Game: {game_label})"), interaction)
                    role_lookup_errors.append(game_label)
                    continue

                if role.id not in seen_role_ids:
                    roles_to_add.append(role)
                    seen_role_ids.add(role.id)
                    assigned_roles_display.append(role.name)

            if roles_to_add:
                try:
                    await interaction.user.add_roles(*roles_to_add, reason=f"BWC onboarding: primary={primary_game}; additional={_format_game_list(secondary_games)}")
                except Exception as e:
                    await log_error(e, interaction)
                    error_msg = "Failed to assign one or more requested roles. Please contact an Admin."

            if role_lookup_errors and not error_msg:
                error_msg = f"One or more configured roles were not found: **{_format_game_list(role_lookup_errors)}**. Please contact an Admin."

        if not error_msg:
            await self.run_mimic_check_if_needed()

        await self.send_audit_log(interaction, error_msg)

        if not error_msg and primary_game in config.GAME_ROLES:
            await self.send_primary_game_command_alert(interaction)

        if not error_msg and self.star_citizen_selected() and primary_game != STAR_CITIZEN_LABEL:
            await self.send_star_citizen_secondary_command_alert(interaction)

        if error_msg:
            final_msg = f"⚠️ **Attention Needed**\nYour onboarding info was saved, but we encountered an issue:\n> {error_msg}\n\nPlease contact a Moderator or Admin for assistance."
            if assigned_roles_display:
                final_msg += f"\n\nRoles applied before the issue: **{', '.join(assigned_roles_display)}**"
        else:
            final_msg = "✅ **You are all set!** Welcome to the server."
            if selected_games:
                final_msg += f"\nPrimary Game: **{primary_game}**"
                final_msg += f"\nAdditional Games: **{_format_game_list(secondary_games)}**"
                final_msg += f"\nAssigned Roles: **{', '.join(assigned_roles_display)}**"
            elif primary_game == "None":
                final_msg += "\nAssigned Role: **Guest**"

        await interaction.edit_original_response(content=final_msg, view=None)

    async def send_primary_game_command_alert(self, interaction: discord.Interaction):
        try:
            if not interaction.guild:
                return

            primary_game = self.answers.get("game")
            if primary_game not in config.GAME_ROLES:
                return

            game_config = config.GAME_ROLES[primary_game]
            command_channel_id = game_config.get("command_channel_id")
            if not command_channel_id:
                return

            command_channel = interaction.guild.get_channel(command_channel_id) or self.bot.get_channel(command_channel_id)
            if not command_channel:
                await log_error(
                    ValueError(f"Command channel ID not found for {primary_game}: {command_channel_id}"),
                    interaction,
                )
                return

            secondary_games = self.answers.get("secondary_games") or []

            embed = discord.Embed(
                title=_env_title(f"📣 {primary_game} Onboarding Complete"),
                description=(
                    f"{interaction.user.mention} (`{interaction.user.id}`) has completed Onboarding.\n\n"
                    "Reach out to the member and get them started on submitting a recruitment application "
                    "and attending an Op."
                ),
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="User", value=f"{interaction.user.mention}\n`{interaction.user.name}`", inline=True)
            embed.add_field(name="Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="Environment", value=config.ENVIRONMENT, inline=True)
            embed.add_field(name="Primary Game", value=primary_game, inline=True)
            embed.add_field(name="Additional Games", value=_format_game_list(secondary_games), inline=True)
            if primary_game == STAR_CITIZEN_LABEL and self.answers.get("rsi_profile_url"):
                embed.add_field(name="RSI Citizen Profile", value=self.answers["rsi_profile_url"], inline=False)
                self.add_mimic_check_field(embed)
            embed.add_field(
                name="Action Needed",
                value="Contact the member, direct them to submit a recruitment application, and help them get scheduled for an Op.",
                inline=False,
            )
            embed.add_field(name="Status", value="🟡 Unresolved — awaiting leadership outreach.", inline=False)

            ping_content = None
            staff_ping_role_id = game_config.get("staff_ping_role_id")
            if staff_ping_role_id:
                staff_role = interaction.guild.get_role(staff_ping_role_id)
                if staff_role:
                    ping_content = staff_role.mention

            await command_channel.send(
                content=ping_content,
                embed=embed,
                view=CommandOutreachView(interaction.user.id, primary_game),
                allowed_mentions=discord.AllowedMentions(roles=True if ping_content else False),
            )
        except Exception as e:
            await log_error(e, interaction)


    async def send_star_citizen_secondary_command_alert(self, interaction: discord.Interaction):
        """Notify Star Citizen C&S when SC is selected as an additional game.

        The RSI profile URL is deliberately posted only to the private Star Citizen command
        alert and not to the general onboarding audit log.
        """
        try:
            if not interaction.guild:
                return

            primary_game = self.answers.get("game")
            secondary_games = self.answers.get("secondary_games") or []
            if primary_game == STAR_CITIZEN_LABEL or STAR_CITIZEN_LABEL not in secondary_games:
                return

            game_config = config.GAME_ROLES.get(STAR_CITIZEN_LABEL, {})
            command_channel_id = game_config.get("command_channel_id")
            if not command_channel_id:
                return

            command_channel = interaction.guild.get_channel(command_channel_id) or self.bot.get_channel(command_channel_id)
            if not command_channel:
                await log_error(
                    ValueError(f"Command channel ID not found for Star Citizen: {command_channel_id}"),
                    interaction,
                )
                return

            embed = discord.Embed(
                title=_env_title("📣 Star Citizen Additional Game Selected"),
                description=(
                    f"{interaction.user.mention} (`{interaction.user.id}`) completed Onboarding and selected "
                    "**Star Citizen** as an additional game.\n\n"
                    "Review the RSI Citizen profile below and reach out if Star Citizen follow-up is needed."
                ),
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="User", value=f"{interaction.user.mention}\n`{interaction.user.name}`", inline=True)
            embed.add_field(name="Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="Environment", value=config.ENVIRONMENT, inline=True)
            embed.add_field(name="Primary Game", value=primary_game or "None", inline=True)
            embed.add_field(name="Additional Games", value=_format_game_list(secondary_games), inline=True)
            if self.answers.get("rsi_profile_url"):
                embed.add_field(name="RSI Citizen Profile", value=self.answers["rsi_profile_url"], inline=False)
                self.add_mimic_check_field(embed)
            embed.add_field(
                name="Action Needed",
                value="Review the RSI profile and coordinate Star Citizen onboarding follow-up if needed.",
                inline=False,
            )
            embed.add_field(name="Status", value="🟡 Unresolved — awaiting Star Citizen leadership review.", inline=False)

            ping_content = None
            staff_ping_role_id = game_config.get("staff_ping_role_id")
            if staff_ping_role_id:
                staff_role = interaction.guild.get_role(staff_ping_role_id)
                if staff_role:
                    ping_content = staff_role.mention

            await command_channel.send(
                content=ping_content,
                embed=embed,
                view=CommandOutreachView(interaction.user.id, STAR_CITIZEN_LABEL),
                allowed_mentions=discord.AllowedMentions(roles=True if ping_content else False),
            )
        except Exception as e:
            await log_error(e, interaction)

    async def send_audit_log(self, interaction: discord.Interaction, error_msg: str = None):
        try:
            log_channel = interaction.guild.get_channel(config.JOIN_LOGS_CHANNEL_ID) if interaction.guild else self.bot.get_channel(config.JOIN_LOGS_CHANNEL_ID)
            if not log_channel:
                return

            primary_game = self.answers.get("game", "None")
            secondary_games = self.answers.get("secondary_games") or []

            embed = discord.Embed(
                title=_env_title("📥 Onboarding Complete") if not error_msg else _env_title("⚠️ Onboarding Incomplete"),
                color=discord.Color.green() if not error_msg else discord.Color.orange(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="User", value=f"{interaction.user.mention}\n`{interaction.user.name}`", inline=True)
            embed.add_field(name="Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="Environment", value=config.ENVIRONMENT, inline=True)
            embed.add_field(name="Reason", value=self.answers.get("reason", "Unknown"), inline=True)
            embed.add_field(name="Primary Game", value=primary_game, inline=True)
            embed.add_field(name="Additional Games", value=_format_game_list(secondary_games), inline=True)
            embed.add_field(name="Rules Accepted", value=self.answers.get("rules", "No"), inline=True)
            embed.add_field(name="SOP Understood", value=self.answers.get("sop", "No"), inline=True)

            if error_msg:
                embed.add_field(name="⚠️ Error Warning", value=error_msg, inline=False)

            ping_content = None
            if primary_game in config.GAME_ROLES:
                staff_ping_role_id = config.GAME_ROLES[primary_game].get("staff_ping_role_id")
                if staff_ping_role_id and interaction.guild:
                    staff_role = interaction.guild.get_role(staff_ping_role_id)
                    if staff_role:
                        ping_content = staff_role.mention

            await log_channel.send(
                content=ping_content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True if ping_content else False),
            )
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
        self._start_view_registered = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._start_view_registered:
            self.bot.add_view(StartView(self.bot))
            self._start_view_registered = True
            print(f"Registered persistent onboarding start view for {config.ENVIRONMENT}.")

        if config.START_CHANNEL_ID:
            channel = self.bot.get_channel(config.START_CHANNEL_ID)
            if channel:
                async for msg in channel.history(limit=50):
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

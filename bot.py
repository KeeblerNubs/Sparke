"""Discord invite-role bot entry point.

This bot listens for member joins and assigns roles based on the invite code
used during the join. It exposes commands for managing invite-role mappings.

The bot expects a bot token supplied via the ``DISCORD_TOKEN`` environment
variable. When running under Docker (see ``Dockerfile``) this variable is
passed through from the host.
"""
from __future__ import annotations

import logging
import os
from typing import Dict

import discord
from discord import app_commands
from discord.ext import commands

# Configure basic logging so container logs surface useful information
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Intents for tracking invites and members
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
# ``message_content`` intent is required for prefix commands to function.
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store invite-to-role mappings {invite_code: role_id}
invite_role_map: Dict[str, int] = {}
# Dictionary to track uses of invites per guild {guild_id: {invite_code: uses}}
invite_uses: Dict[int, Dict[str, int]] = {}
commands_synced = False


def build_invite_mapping_text(guild: discord.Guild) -> str:
    """Render all tracked invite-role mappings for a guild as user-friendly text."""
    if not invite_role_map:
        return "No invite-role mappings set up yet."

    lines = []
    for code, role_id in invite_role_map.items():
        role = guild.get_role(role_id)
        role_name = role.name if role else "Deleted Role"
        lines.append(f"Invite `{code}` → Role `{role_name}`")
    return "\n".join(lines)


class DashboardView(discord.ui.View):
    """Top-level dashboard with separate admin and user controls."""

    def __init__(self) -> None:
        super().__init__(timeout=180)

    @discord.ui.button(label="Admin Control", style=discord.ButtonStyle.danger, emoji="🛠️")
    async def admin_control(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This menu can only be used inside a server.", ephemeral=True
            )
            return

        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the **Manage Server** permission to use admin controls.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🛠️ Admin Dashboard",
            description="Use these controls to manage invite-role mappings.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Tracked mappings", value=build_invite_mapping_text(interaction.guild), inline=False)
        await interaction.response.send_message(embed=embed, view=AdminControlView(), ephemeral=True)

    @discord.ui.button(label="User Control", style=discord.ButtonStyle.primary, emoji="👤")
    async def user_control(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This menu can only be used inside a server.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="👤 User Dashboard",
            description="Quick actions and help for server members.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Available tracked invites", value=build_invite_mapping_text(interaction.guild), inline=False)
        embed.add_field(
            name="Need a custom invite?",
            value="Contact an admin and ask them to run `!createinvite @Role [max_uses] [max_age]`.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, view=UserControlView(), ephemeral=True)


class AdminControlView(discord.ui.View):
    """Admin-only popup actions."""

    def __init__(self) -> None:
        super().__init__(timeout=180)

    @discord.ui.button(label="Refresh Mappings", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_mappings(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Server context not found.", ephemeral=True)
            return

        await interaction.response.send_message(build_invite_mapping_text(interaction.guild), ephemeral=True)

    @discord.ui.button(label="Clear Mappings", style=discord.ButtonStyle.danger, emoji="🧹")
    async def clear_mappings(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or not member.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need the **Manage Server** permission to clear mappings.",
                ephemeral=True,
            )
            return

        invite_role_map.clear()
        logger.info("Invite-role mappings cleared using dashboard by %s", member)
        await interaction.response.send_message("All invite-role mappings were cleared.", ephemeral=True)


class UserControlView(discord.ui.View):
    """User-focused popup actions."""

    def __init__(self) -> None:
        super().__init__(timeout=180)

    @discord.ui.button(label="How roles are assigned", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def role_help(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "When someone joins through a tracked invite link, the mapped role is applied automatically.",
            ephemeral=True,
        )


@bot.event
async def on_ready() -> None:
    global commands_synced

    logger.info("Logged in as %s", bot.user)
    # Initialize invite uses
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
        except discord.Forbidden:
            logger.warning("Missing permissions to view invites for guild %s", guild.name)
            continue
        invite_uses[guild.id] = {invite.code: invite.uses for invite in invites}
    logger.info("Cached invite usage for %d guild(s)", len(invite_uses))

    if not commands_synced:
        synced_commands = await bot.tree.sync()
        commands_synced = True
        logger.info("Synced %d application command(s)", len(synced_commands))


@bot.command(name="dashboard")
@commands.guild_only()
async def dashboard_prefix(ctx: commands.Context) -> None:
    """Open an interactive dashboard with admin and user popup controls."""
    embed = discord.Embed(
        title="📊 Server Dashboard",
        description="Use the buttons below to open the admin or user popup menus.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed, view=DashboardView())


@bot.tree.command(name="dashboard", description="Open a popup dashboard for admin and user controls")
@app_commands.guild_only()
async def dashboard_slash(interaction: discord.Interaction) -> None:
    """Slash-command version of the interactive dashboard."""
    embed = discord.Embed(
        title="📊 Server Dashboard",
        description="Use the buttons below to open the admin or user popup menus.",
        color=discord.Color.green(),
    )
    await interaction.response.send_message(embed=embed, view=DashboardView(), ephemeral=True)


@bot.command(name="createinvite")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def create_invite(ctx: commands.Context, role: discord.Role, max_uses: int = 0, max_age: int = 0) -> None:
    """Create an invite linked to a specific role.

    Example: ``!createinvite @Role 5 3600``
    """
    invite = await ctx.channel.create_invite(max_uses=max_uses, max_age=max_age, unique=True)
    invite_role_map[invite.code] = role.id
    await ctx.send(f"🔗 Invite created: {invite.url} (Grants role: {role.name})")
    logger.info("Created invite %s mapped to role %s (%s)", invite.code, role.name, role.id)


@bot.command(name="listinvites")
@commands.guild_only()
async def list_invites(ctx: commands.Context) -> None:
    """List all active invite-to-role mappings."""
    await ctx.send(build_invite_mapping_text(ctx.guild))


@bot.command(name="clearinvites")
@commands.guild_only()
@commands.has_permissions(manage_guild=True)
async def clear_invites(ctx: commands.Context) -> None:
    """Clear all invite-role mappings."""
    invite_role_map.clear()
    await ctx.send("🧹 Cleared all invite-role mappings.")
    logger.info("Invite-role mappings cleared in guild %s", ctx.guild.name if ctx.guild else "DM")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    guild = member.guild
    try:
        invites = await guild.invites()
    except discord.Forbidden:
        logger.warning("Missing permissions to view invites for guild %s", guild.name)
        return

    old_uses = invite_uses.get(guild.id, {})

    # Find which invite was used
    used_invite = None
    for invite in invites:
        if old_uses.get(invite.code, 0) < invite.uses:
            used_invite = invite
            break

    # Update stored invite uses
    invite_uses[guild.id] = {invite.code: invite.uses for invite in invites}

    if used_invite and used_invite.code in invite_role_map:
        role_id = invite_role_map[used_invite.code]
        role = guild.get_role(role_id)
        if role is None:
            logger.warning("Role %s not found in guild %s", role_id, guild.name)
            return
        try:
            await member.add_roles(role, reason=f"Joined using invite {used_invite.code}")
        except discord.Forbidden:
            logger.warning("Missing permissions to assign role %s in guild %s", role.name, guild.name)
            return
        logger.info("Assigned role %s to %s via invite %s", role.name, member.display_name, used_invite.code)


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    bot.run(token)


if __name__ == "__main__":
    main()

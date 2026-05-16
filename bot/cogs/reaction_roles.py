"""
cogs/reaction_roles.py  —  on_raw_reaction_add / on_raw_reaction_remove
                            + /reactionrole add slash command
"""
import discord
from discord.ext import commands
from discord import app_commands

from database import reaction_roles, save_reaction_roles
from utils import log_command


class ReactionRolesCog(commands.Cog, name="ReactionRoles"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    reactionrole_group = app_commands.Group(name="reactionrole", description="Manage reaction roles")

    @reactionrole_group.command(name="add", description="Add a reaction role to a message")
    @app_commands.describe(message_id="The ID of the message", emoji="The emoji to react with", role="The role to give")
    @app_commands.default_permissions(manage_roles=True)
    async def reactionrole_add(self, interaction: discord.Interaction,
                               message_id: str, emoji: str, role: discord.Role):
        log_command("reactionrole_add")
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            await message.add_reaction(emoji)
            reaction_roles.setdefault(message_id, {})[emoji] = role.id
            save_reaction_roles()
            await interaction.response.send_message(
                f"✅ Bound {role.mention} to {emoji} on message `{message_id}`.", ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message("❌ Message not found in this channel.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I can't add reactions to that message.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member and payload.member.bot:
            return
        msg_id    = str(payload.message_id)
        emoji_str = str(payload.emoji.name)
        if msg_id in reaction_roles and emoji_str in reaction_roles[msg_id]:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                role = guild.get_role(reaction_roles[msg_id][emoji_str])
                if role:
                    try:
                        await payload.member.add_roles(role)
                    except Exception as e:
                        print(f"[RxRoles] Error giving role: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        msg_id    = str(payload.message_id)
        emoji_str = str(payload.emoji.name)
        if msg_id in reaction_roles and emoji_str in reaction_roles[msg_id]:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                role   = guild.get_role(reaction_roles[msg_id][emoji_str])
                member = guild.get_member(payload.user_id)
                if role and member and not member.bot:
                    try:
                        await member.remove_roles(role)
                    except Exception as e:
                        print(f"[RxRoles] Error removing role: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRolesCog(bot))

"""
cogs/welcome.py  —  on_member_join / on_member_remove + easy_pil welcome cards
"""
import discord
from discord.ext import commands

import database as db
from database import level_requirements, user_names, save_user_names
from config import (
    WELCOME_CHANNEL_ID, LEAVE_CHANNEL_ID,
    WELCOME_MESSAGE, LEAVE_MESSAGE, AUTO_ROLES,
)


class WelcomeCog(commands.Cog, name="Welcome"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Cache display name
        db.cache_member_name(member)

        # Welcome message
        if WELCOME_CHANNEL_ID:
            channel = member.guild.get_channel(int(WELCOME_CHANNEL_ID))
            if channel:
                try:
                    embed = discord.Embed(
                        title="👋 Welcome!",
                        description=WELCOME_MESSAGE.format(
                            mention=member.mention,
                            server=member.guild.name,
                            count=member.guild.member_count,
                        ),
                        color=discord.Color.green(),
                    )
                    if member.display_avatar:
                        embed.set_thumbnail(url=member.display_avatar.url)
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"[Welcome] Error sending welcome: {e}")

        # Auto-roles
        for role_id in AUTO_ROLES:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role)
                except Exception as e:
                    print(f"[Welcome] Auto-role error: {e}")

        # Level 0 default role
        req_0 = level_requirements.get("0")
        if req_0:
            role_id = req_0.get("role_id")
            role    = None
            if role_id and role_id != 0:
                role = member.guild.get_role(role_id)
            if not role:
                role = discord.utils.get(member.guild.roles, name="Level 0")
            if role:
                try:
                    await member.add_roles(role)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if LEAVE_CHANNEL_ID:
            channel = member.guild.get_channel(int(LEAVE_CHANNEL_ID))
            if channel:
                try:
                    embed = discord.Embed(
                        title="👋 Goodbye!",
                        description=LEAVE_MESSAGE.format(
                            name=member.display_name,
                            server=member.guild.name,
                        ),
                        color=discord.Color.red(),
                    )
                    if member.display_avatar:
                        embed.set_thumbnail(url=member.display_avatar.url)
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"[Welcome] Error sending leave: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))

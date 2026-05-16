import discord
from typing import Optional, List
from .utils import get_emoji

class EmbedFactory:
    @staticmethod
    def create_embed(
        title: str,
        description: str,
        color: discord.Color = discord.Color.blue(),
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        footer: Optional[str] = None,
        fields: Optional[List[dict]] = None
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if image:
            embed.set_image(url=image)
        if footer:
            embed.set_footer(text=footer)
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", "Field"),
                    value=field.get("value", "..."),
                    inline=field.get("inline", True)
                )
        return embed

    @staticmethod
    def error_embed(message: str) -> discord.Embed:
        return EmbedFactory.create_embed(
            f"{get_emoji('error')} Error",
            message,
            discord.Color.red()
        )

    @staticmethod
    def success_embed(message: str) -> discord.Embed:
        return EmbedFactory.create_embed(
            f"{get_emoji('success')} Success",
            message,
            discord.Color.green()
        )

    @staticmethod
    def info_embed(message: str) -> discord.Embed:
        return EmbedFactory.create_embed(
            f"{get_emoji('info')} Information",
            message,
            discord.Color.blue()
        )

    @staticmethod
    def game_lobby_embed(
        game_name: str,
        host: discord.Member,
        players: List[discord.Member],
        max_players: Optional[int] = None,
        rules: Optional[str] = None
    ) -> discord.Embed:
        player_count = len(players)
        limit = f"/{max_players}" if max_players else ""
        
        desc = f"**Host:** {host.mention}\n"
        desc += f"**Players:** {player_count}{limit}\n"
        desc += f"**Status:** Waiting for players...\n\n"
        
        if rules:
            desc += f"**Rules:**\n{rules}\n\n"
            
        player_list = "\n".join([f"{i+1}. {p.mention}" for i, p in enumerate(players)])
        desc += f"**Current Players:**\n{player_list}"
        
        return EmbedFactory.create_embed(
            f"{get_emoji('game')} Lobby: {game_name}",
            desc,
            discord.Color.gold()
        )

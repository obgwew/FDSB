# cmds_FDScripts/createRole.py
import discord
from FDScript import ExecutionContext, Command
from FDCore import FDSyntaxError, FDLogicError, _send_error, _parse_color

def _cosmetic_perms() -> discord.Permissions:
    return discord.Permissions.none()


def _member_perms() -> discord.Permissions:
    return discord.Permissions(
        create_instant_invite=True,
        change_nickname=True,
        send_messages=True,
        add_reactions=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        use_external_emojis=True,
        connect=True,
        speak=True,
        use_voice_activation=True,
    )


def _mod_perms() -> discord.Permissions:
    perms = _member_perms()
    perms.update(
        manage_messages=True,
        manage_nicknames=True,
        kick_members=True,
        ban_members=True,
        mute_members=True,
        deafen_members=True,
        move_members=True,
        moderate_members=True, 
        view_audit_log=True,
    )
    return perms


def _manager_perms() -> discord.Permissions:
    perms = _mod_perms()
    perms.update(
        manage_channels=True,
        manage_roles=True,
        manage_webhooks=True,
        manage_threads=True,
        manage_events=True,
        manage_emojis=True,     
        manage_guild=True,
    )
    return perms

_ROLE_PRESET_PERMS = {
    "cosmetic":  _cosmetic_perms,
    "member":    _member_perms,
    "mod":       _mod_perms,
    "moderator": _mod_perms,
    "manager":   _manager_perms,
    "admin":    _manager_perms,
}


def _resolve_permissions(raw: str) -> discord.Permissions | None:
    
    key = raw.strip().lower()
    if key in _ROLE_PRESET_PERMS:
        return _ROLE_PRESET_PERMS[key]()
    try:
        return discord.Permissions(int(key, 0))
    except ValueError:
        return None


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in ("true", "yes", "on", "1")


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 3:
        await _send_error(ch, FDSyntaxError(
            "`$createRole` requires at least 3 arguments: "
            "`$createRole[role name; color; permissions; (display role; mention role)]`\n"
            "`permissions` can be `cosmetic`, `member`, `mod`, `manager`, or a raw permission number."
        ))
        return

    role_name  = args[0].strip()
    color_raw  = args[1].strip()
    perms_raw  = args[2].strip()
    hoist       = _parse_bool(args[3]) if len(args) > 3 and args[3].strip() else False
    mentionable = _parse_bool(args[4]) if len(args) > 4 and args[4].strip() else False

    if not role_name:
        await _send_error(ch, FDLogicError("`$createRole` — the role name (1st arg) cannot be empty"))
        return

    if len(role_name) > 100:
        await _send_error(ch, FDLogicError("`$createRole` — role names can't exceed 100 characters"))
        return

    guild = ctx.message.guild if ctx.message else None
    if guild is None:
        await _send_error(ch, FDLogicError("`$createRole` — this command can't be used outside of a server"))
        return

    color_value = _parse_color(color_raw) if color_raw else 0x000000

    permissions = _resolve_permissions(perms_raw)
    if permissions is None:
        await _send_error(ch, FDLogicError(
            f"`$createRole` — invalid permissions value `{args[2]}`. "
            f"Use a preset (`cosmetic`, `member`, `mod`, `manager`) or a raw permission number."
        ))
        return

    author_name = ctx.message.author.name if getattr(ctx.message, 'author', None) else 'FDScript'

    try:
        role = await guild.create_role(
            name=role_name,
            colour=discord.Colour(color_value),
            permissions=permissions,
            hoist=hoist,
            mentionable=mentionable,
            reason=f"Created via $createRole by {author_name}"
        )
    except discord.Forbidden:
        await _send_error(ch, FDLogicError(
            "`$createRole` — the bot doesn't have the `Manage Roles` permission needed to create roles"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDLogicError(f"`$createRole` — failed to create the role: `{e}`"))
        return

    ctx.return_vars['createdRoleID'] = str(role.id)
    ctx.log_event(
        f"$createRole → created [{role.name}] (ID {role.id}) "
        f"color=#{color_value:06X} perms={perms_raw} hoist={hoist} mentionable={mentionable}"
    )
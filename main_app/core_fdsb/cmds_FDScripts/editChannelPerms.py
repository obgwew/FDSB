# cmds_FDScripts/editChannelPerms.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError, FDRuntimeError,
    _send_error, _PERMISSION_NAMES
)


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 3:
        await _send_error(ch, FDSyntaxError(
            "`$editChannelPerms` requires at least 3 arguments: "
            "`$editChannelPerms[channelID; targetID; perm1; (perm2; ...)]`"
        ))
        return

    channel_id_raw = ctx.resolve(args[0]).strip()
    if not channel_id_raw.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$editChannelPerms` — channel ID must be numeric, got `{channel_id_raw}`"
        ))
        return

    guild = getattr(ctx.message, 'guild', None)
    if guild is None:
        await _send_error(ch, FDEnvironmentError(
            "`$editChannelPerms` cannot be used outside of a server (Guild)"
        ))
        return

    channel = guild.get_channel(int(channel_id_raw))
    if channel is None:
        try:
            channel = await guild.fetch_channel(int(channel_id_raw))
        except discord.NotFound:
            await _send_error(ch, FDEnvironmentError(
                f"`$editChannelPerms` — channel `{channel_id_raw}` not found in this server"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDRuntimeError(
                f"`$editChannelPerms` — failed to fetch channel `{channel_id_raw}`: `{e.text}`"
            ))
            return

    target_id_raw = ctx.resolve(args[1]).strip()
    cleaned_target_id = re.sub(r'[<@&!>]', '', target_id_raw)

    if not cleaned_target_id.isdigit():
        await _send_error(ch, FDLogicError(
            f"`$editChannelPerms` — target ID/mention must be valid, got `{target_id_raw}`"
        ))
        return

    target_id = int(cleaned_target_id)
    target: discord.Role | discord.Member | None = guild.get_role(target_id) or guild.get_member(target_id)

    if target is None:
        try:
            target = await guild.fetch_member(target_id)
        except discord.NotFound:
            await _send_error(ch, FDEnvironmentError(
                f"`$editChannelPerms` — no member or role found with ID `{target_id_raw}` in this server"
            ))
            return
        except discord.HTTPException as e:
            await _send_error(ch, FDRuntimeError(
                f"`$editChannelPerms` — failed to fetch member `{target_id_raw}`: `{e.text}`"
            ))
            return

    perm_inputs = []
    for arg in args[2:]:
        resolved = ctx.resolve(arg).strip()
        if resolved:
            perm_inputs.extend(resolved.split())

    if not perm_inputs:
        await _send_error(ch, FDLogicError(
            "`$editChannelPerms` — no valid permissions provided"
        ))
        return

    overwrite = channel.overwrites_for(target)
    updated_perms = []

    for item in perm_inputs:
        state = True
        raw_perm = item.strip().lower()

        if raw_perm.startswith('+'):
            state = True
            raw_perm = raw_perm[1:]
        elif raw_perm.startswith('-'):
            state = False
            raw_perm = raw_perm[1:]
        elif raw_perm.startswith('/') or raw_perm.startswith('~'):
            state = None
            raw_perm = raw_perm[1:]

        raw_perm = raw_perm.strip()

        if raw_perm not in _PERMISSION_NAMES:
            await _send_error(ch, FDLogicError(
                f"`$editChannelPerms` — unknown permission name `{raw_perm}`.\n"
                f"Valid examples: `send_messages`, `view_channel`, `connect`, `manage_roles`"
            ))
            return

        setattr(overwrite, raw_perm, state)
        sign = "+" if state is True else ("-" if state is False else "/")
        updated_perms.append(f"{sign}{raw_perm}")

    try:
        await channel.set_permissions(target, overwrite=overwrite, reason=f"FDScript editChannelPerms by {ctx.message.author}")
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$editChannelPerms` — bot lacks `Manage Channels` or `Manage Permissions` permission in this channel"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDRuntimeError(
            f"`$editChannelPerms` — failed to update channel permissions: `{e.text}`"
        ))
        return

    ctx.log_event(f"editChannelPerms → updated perms for {target} ({', '.join(updated_perms)}) in #{channel.name}")
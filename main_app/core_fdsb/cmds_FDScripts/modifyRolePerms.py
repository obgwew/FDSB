# cmds_FDScripts/modifyRolePerms.py
import re
import discord
from FDScript import (
    ExecutionContext, Command,
    FDSyntaxError, FDLogicError, FDEnvironmentError,
    _send_error, _truncate, _PERMISSION_NAMES,
)

_ROLE_MENTION_RE = re.compile(r'^<@&(\d+)>$')


def resolve_inline(args: list[str], ctx: ExecutionContext) -> str:
    return ""


def _resolve_role_id(raw: str) -> int | None:
    raw = raw.strip()
    match = _ROLE_MENTION_RE.match(raw)
    if match:
        return int(match.group(1))
    if raw.isdigit():
        return int(raw)
    return None


def _parse_perm_token(raw: str) -> tuple[str, bool] | None:
    """Returns (permission_name, add_flag). Sign defaults to '+' when absent."""
    raw = raw.strip()
    if not raw:
        return None

    sign = '+'
    if raw[0] in ('+', '-'):
        sign = raw[0]
        raw = raw[1:].strip()

    name = raw.lower()
    if not name:
        return None
    if name == "all":
        return "all", sign == '+'
    if name not in _PERMISSION_NAMES:
        return None
    return name, sign == '+'


async def execute(cmd: Command, args: list[str], ctx: ExecutionContext, ch: discord.abc.Messageable) -> None:
    if len(args) < 2:
        await _send_error(ch, FDSyntaxError(
            "`$editRolePerms` requires at least 2 arguments: "
            "`$editRolePerms[role id; permission +/-; ...]`\n"
            "No `+`/`-` prefix defaults to `+`. Only listed permissions are touched — "
            "anything not mentioned keeps its current value."
        ))
        return

    if not getattr(ctx.message, "guild", None):
        await _send_error(ch, FDEnvironmentError(
            "`$editRolePerms` — this command can only be used inside a server"
        ))
        return

    role_id_str = ctx.resolve(args[0]).strip()
    role_id = _resolve_role_id(role_id_str)
    if role_id is None:
        await _send_error(ch, FDLogicError(
            f"`$editRolePerms` — invalid role reference `{role_id_str}` "
            f"(expected a role mention or a numeric ID)"
        ))
        return

    role = ctx.message.guild.get_role(role_id)
    if role is None:
        await _send_error(ch, FDLogicError(
            f"`$editRolePerms` — no role found with ID `{role_id}`"
        ))
        return

    changes: list[tuple[str, bool]] = []
    invalid: list[str] = []

    for tok in args[1:]:
        resolved = ctx.resolve(tok).strip()
        if not resolved:
            continue
        parsed = _parse_perm_token(resolved)
        if parsed is None:
            invalid.append(resolved)
            continue
        changes.append(parsed)

    if invalid:
        await _send_error(ch, FDLogicError(
            f"`$editRolePerms` — unknown permission name(s): {', '.join(f'`{v}`' for v in invalid)}"
        ))
        return

    if not changes:
        await _send_error(ch, FDLogicError(
            "`$editRolePerms` — no valid permission changes were given"
        ))
        return

    new_perms = discord.Permissions(role.permissions.value)
    applied_log: list[str] = []

    for name, add in changes:
        if name == "all":
            new_perms = discord.Permissions.all() if add else discord.Permissions.none()
        else:
            setattr(new_perms, name, add)
        applied_log.append(f"{'+' if add else '-'}{name}")

    try:
        await role.edit(
            permissions=new_perms,
            reason=f"Edited via $editRolePerms by {ctx.message.author} ({ctx.message.author.id})",
        )
    except discord.Forbidden:
        await _send_error(ch, FDEnvironmentError(
            "`$editRolePerms` — bot lacks `Manage Roles` permission, or that role is "
            "higher than (or equal to) the bot's own top role"
        ))
        return
    except discord.HTTPException as e:
        await _send_error(ch, FDEnvironmentError(
            f"`$editRolePerms` — failed to edit role: HTTP {e.status}: {e.text}"
        ))
        return
    except Exception as ex:
        await _send_error(ch, FDLogicError(f"`$editRolePerms` — unexpected error: {ex}"))
        return

    ctx.stop_typing()
    dest = await ctx.get_dest()
    sent = await dest.send(f"✅ Updated permissions for <@&{role.id}>")
    ctx.last_bot_message = sent

    ctx.log_event(
        f"editRolePerms → `{_truncate(role.name)}` ({role.id}): {', '.join(applied_log)}"
    )
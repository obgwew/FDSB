# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/definitions.py


KNOWN_COMMANDS: set[str] = {
    # a
    "addBotReactions", "addButton", "addSelectMenuOption", "addTimestamp", "addUserReactions",
    "and", "author", "authorAvatar", "authorIcon", "authorID",
    "authorName", "authorServerAvatar", "authorURL",
    # b
    "ban", "blackListRoles", "blackListServer", "blackListUsers", "boostCount",
    "boostLevel", "botID", "botLeave", "botName", "break",
    # c
    "call", "ceil", "changeUsername", "channelExists", "channelID",
    "channelName", "channelType", "charCount", "checkContains", "clear",
    "clientTyping", "cloneChannel", "cloneRole", "color", "cooldown",
    "createChannel", "createRole", "cropText", "customID",
    # d
    "deleteChannels", "deletecommand", "deleteRole", "description", "displayName",
    "div", "dm", "day",
    # e
    "editButton", "editChannelPerms", "editChannelTopic", "editIn", "editMessage",
    "editSelectMenu", "editSelectMenuOption", "editSplitOut", "elif", "else",
    "emojiExists", "emojiName", "endfor", "endfunc", "endif",
    "endwhile", "ephemeral",
    # f
    "findChannel", "findRole", "floor", "footer", "footerIcon",
    "for", "func",
    # g
    "getBotInvent", "getCreationDateTimestamp", "getGuildVar", "getLeaderboardPosition", "getLeaderboardValue",
    "getMessage", "getServerInvite", "getSplitOutLength", "getTimestamp", "getUserStatus",
    "getUserVar", "getVar", "globalUserLeaderboard", "guildBanner", "guildID",
    "guildName", "guildVerificationLvl",
    # h
    "hour", "httpAddHeader", "httpDelete", "httpGet", "httpPatch",
    "httpPost", "httpPut", "httpResult", "httpStatus",
    # i
    "if", "image", "isAdmin", "isBooster", "isBot",
    "isNSFW", "isNumber", "isOwner",
    # j
    "joinSplitOut",
    # k
    "kick",
    # l
    "lastBotMessageID", "lastUserMessageID", "lineCount", "log",
    # m
    "math", "membersCount", "mention", "message", "messageID",
    "minute", "mod", "modifyChannel", "modifyRolePerms", "month",
    "moveChannel", "mul",
    # n
    "newSelectMenu", "numberAbbreviate", "numberSeparator",
    # o
    "onlyAdmin", "onlyBotPerms", "onlyFor", "onlyIf", "onlyIn",
    "onlyNSFW", "onlyUserPerms", "or",
    # p
    "ping", "power",
    # r
    "randomint", "randomRoleID", "randomRoleMention", "randomstr", "randomUserID",
    "removeAllComponents", "removeButtons", "removeComponent", "removeLinks", "removeSplitOutElement",
    "repeatMessage", "replaceRegex", "replaceText", "reply", "replyIn",
    "resetGuildVar", "resetUserVar", "return", "returnGetReactions", "returnGuildBansID",
    "returnGuildChannelsID", "returnGuildEmojisID", "returnGuildRolesID", "returnGuildUsersID", "roleAssign",
    "round",
    # s
    "second", "sendEmbedMessage", "sendMessage", "serverIcon", "serverLeaderboard",
    "serverOwnerID", "setBotStatus", "setGuildVar", "setUserVar", "setVar",
    "slowmode", "splitIn", "splitOut", "strictArgs", "sub",
    "sum", "suppressErrors", "switch", "syncChannel", "syncMode",
    # t
    "thumbnail", "time", "timeout", "title",
    # u
    "unban", "untimeout", "uptime", "useChannel", "userBanner",
    "userBannerColor", "userLeaderboard",
    # v
    "var", "voiceUsersLimit",
    # w
    "wait", "while",
    # y
    "year",
}

CONTROL_FLOW_COMMANDS: set[str] = {
    "if", "elif", "else", "endif",
    "while", "endwhile",
    "for", "endfor",
    "break", "return",
    "and", "or",
    "onlyIf", "onlyAdmin", "log",
    "onlyUserPerms", "onlyBotPerms", "onlyNSFW", "onlyFor", "onlyIn",
}

FUNCTION_COMMANDS: set[str] = {
    "func", "endfunc", "call",
}

def get_reserved_names() -> set[str]:
    return KNOWN_COMMANDS
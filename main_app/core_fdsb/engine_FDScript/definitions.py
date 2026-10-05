# Copyright (C) 2026 obgwew
# SPDX-License-Identifier: AGPL-3.0-or-later

# main_app/core_fdsb/engine_FDScript/definitions.py


KNOWN_COMMANDS: set[str] = {
    # a
    "addBotReactions", "addButton", "addTimestamp", "addUserReactions", "and",
    "author", "authorIcon", "authorID", "authorName", "authorURL",
    "authorAvatar", "authorServerAvatar", "addSelectMenuOption",
    # b
    "ban", "boostCount", "boostLevel", "botID", "botLeave", "botName", "break",
    # c
    "call", "ceil", "changeUsername", "channelExists", "channelID", "channelName",
    "channelType", "charCount", "checkContains", "clear", "clientTyping", "cloneRole",
    "color", "cooldown", "createChannel", "createRole", "cropText",
    "customID", "cloneChannel",
    # d
    "deleteChannels", "deletecommand", "deleteRole", "description",
    "displayName", "div", "dm",
    # e
    "editButton", "editChannelPerms", "editIn", "editMessage", "editSplitOut",
    "elif", "else", "endfor", "endfunc", "endif",
    "endwhile", "emojiExists", "emojiName", "editSelectMenu", "editSelectMenuOption",
    "editChannelTopic", "ephemeral",
    # f
    "findChannel", "findRole", "floor", "footer", "footerIcon", "for", "func",
    # g
    "getBotInvent", "getCreationDateTimestamp", "getGuildVar","getLeaderboardPosition", "getLeaderboardValue",
    "getMessage", "getServerInvite","getSplitOutLength", "getTimestamp", "getUserStatus",
    "getUserVar", "getVar", "globalUserLeaderboard", "guildID", "guildName",
    "guildVerificationLvl", "guildBanner",
    # h
    "httpAddHeader", "httpDelete", "httpGet", "httpPatch", "httpPost",
    "httpPut", "httpResult", "httpStatus",
    # i
    "if", "image", "isAdmin", "isBooster", "isBot", "isNSFW",
    "isNumber", "isOwner",
    # j
    "joinSplitOut",
    # k
    "kick",
    # l
    "lastBotMessageID", "lastUserMessageID", "log","lineCount",
    # m
    "math", "membersCount", "mention", "message", "messageID",
    "mod", "mul", "modifyRolePerms", "moveChannel", "modifyChannel",
    # n
    "numberSeparator", "numberAbbreviate", "newSelectMenu",
    # o
    "onlyAdmin", "onlyBotPerms", "onlyFor", "onlyIf", "onlyIn", "onlyNSFW", "onlyUserPerms", "or",
    # p
    "ping", "power",
    # r
    "randomint", "randomRoleID", "randomRoleMention", "randomstr","randomUserID",
    "removeButtons", "removeComponent", "removeLinks", "removeSplitOutElement", "repeatMessage",
    "replaceRegex", "replaceText", "reply", "replyIn", "resetGuildVar",
    "resetUserVar", "return","returnGetReactions", "returnGuildBansID", "returnGuildChannelsID",
    "returnGuildEmojisID", "returnGuildRolesID", "returnGuildUsersID", "roleAssign", "round",
    "removeAllComponents",
    # s
    "sendEmbedMessage", "sendMessage", "serverLeaderboard", "serverOwnerID", "setBotStatus",
    "setGuildVar", "setUserVar", "setVar", "slowmode", "splitIn",
    "splitOut", "strictArgs", "sub", "sum", "suppressErrors",
    "switch","serverIcon", "syncChannel", "syncMode",
    # t
    "timeout", "title", "thumbnail",
    # u
    "unban", "untimeout", "uptime", "useChannel", "userBanner",
    "userBannerColor", "userLeaderboard",
    # v
    "var", "voiceUsersLimit",
    # w
    "wait", "while",
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

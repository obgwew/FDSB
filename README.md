![FDSB](./main_app/icons/FDSB.png)

<p>
  <img src="https://img.shields.io/badge/Version-2.5.0-blue?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/badge/Source-AGPL--3.0-blue?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/Languages-12-brightgreen?style=for-the-badge" alt="Languages" />
  <img src="https://img.shields.io/badge/Commands-200+-red?style=for-the-badge" alt="Commands" />
</p>

# FDSB — Free Design Studio Bot

> Build and run Discord bots locally using FDScript, a lightweight, high-level domain-specific language (DSL) designed for this purpose.

---

## Overview

FDSB is a cross-platform application for creating and running Discord bots locally. Bots are programmed in FDScript, a scripting language purpose-built for bot development, which allows them to run efficiently on the user's own device.

**Objective:** To simplify bot development. FDSB requires no hosting, since bots run on-device. It requires no structurally complex code and imposes no programming prerequisites: a working, responsive bot can be created from a short script in approximately 30 seconds.

---

## Getting Started

### Installation (APK / EXE)

1. Download the APK or EXE build compatible with your device.
2. Launch the application. The interface is displayed in English by default.
3. Select **New Bot**. On the page that opens, enter the bot token and bot name, and optionally add a bot image. *(See [Setup Notes](#setup-notes) first.)*
4. Open the bot and go to **Settings** to select the preferred language and interface theme.
5. Consult the **Wiki** page for the full list of available FDScript commands.
6. Open the **Commands** tab and select the **+** button to create a new command. In the editor, enter a command name (required) and choose a prefix. Write the command's code according to the Wiki, then select **Save**.
7. Return to the main screen and select **Start** to run the bot. *(For Android, see [Background Execution](#background-execution).)*

---

## Notes and Warnings

### Setup Notes

> [!NOTE]
> **Discord Developer Portal:** Create your bot and enable all three Gateway Intents (the toggles at the bottom of the **Bot** tab). Then copy the bot token and paste it into the application.

> [!NOTE]
> **Token security:** The token is stored encrypted within the system and cannot be modified by extracting files. This is only available in recent versions: 2.4.3, 2.5.0 and beyond.

> [!NOTE]
> **Bot name and image:** What you configure within the application does not modify the original bot on Discord.

### Background Execution

> [!WARNING]
> The application can run in the background, provided that battery optimization is disabled for it and no network restrictions are applied to it.

> [!CAUTION]
> The settings above are documented for **Android 13 and earlier**. For **Android 14 and later**, background operation is not supported. The only workaround is to convert the application into an "app bubble" and keep it visible on the foreground interface.

### Development Status

> [!NOTE]
> The built-in command set is intentionally kept simple, while more complex tasks are handled by FDScript. This design choice is unrelated to the number of commands planned for future releases.

> [!CAUTION]
> FDScript undergoes gradual changes with each update. Commands may therefore be added, removed, or modified during the Alpha stage. **Sensitive bots should not be built until a stable Beta release is available.**

---

## Changelog

**Alpha stage:** 1.0.0 to 2.x.x (current)

### 1.0.x — Initial Alpha
- New interface, new control mechanism, and FDScript Gen 0
- Fixed Arabic rendering, translator errors, startup crash, and server connection issue

### 2.0.x — Feature Update
- Improved UI, added settings panel and theme support
- Introduced FDScript Gen 1 with 20+ new commands
- Fixed bot file conflicts, themes, and button/input behavior in `commands_view` and `settings_view`
- Replaced the Kivy icon with the BCFD icon

### 2.1.0 — Task Integration and Event Commands
- Added administrative and event commands
- Added bot data upload and download
- Began development of FDScript Gen 2

### 2.2.x — Migration to Flet and Renaming to FDSB
- Migrated the UI framework from Kivy to Flet, with UI effects
- Added APK compatibility (2.2.3)
- Added French, German, Chinese, Russian, and Turkish
- Fixed variable commands, prefix logic, theme/language switching, color-coding, and server issues
- Project officially renamed **FDSB** after 2.2.1

### 2.3.x — Wiki and Channel/HTTP Commands
- Introduced the Wiki interface with faster downloads
- Added channel commands, HTTP commands, and split commands
- Added Polish
- Updated the loading screen, variables view, and command editor
- Fixed Android text colors, themes, and languages

### 2.4.x — New UI, Bot Status, and Stability
- Added embed, function, menu, boost, variable, channel, and leaderboard commands
- Added bot status editor, UI animations, and a more fluid UI architecture
- Added Persian and Urdu
- Began development of FDScript Gen 2.5
- Fixed Android and notification errors, with stability on Android 13 and earlier

### 2.5.0 — CodeEditor and Discord Status
- Added CodeEditor for FDScript
- Added Time/Blacklist commands and Discord Status UI
- Added Indonesian and Spanish
- Fixed several UI issues and commands

---

## Contributors

- @y.lw (Hidden for privacy reasons) — Contributor
- [@obgwew](https://github.com/obgwew) — Programming

---

## License

Copyright (C) 2026 obgwew

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU Affero General Public License** as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

### Additional Permission (AGPL-3.0, Section 7)

A summary only; the full text in the license file governs.

- **Permitted:** You are not required to disclose the source code of your own external server, provided the application connects to it only through the official, unmodified access points (such as a built-in server address field).
- **Not covered:** Concealing that connection from end users. Any modification that does so must be published under this License.
- **Termination:** The permission ends for any modification of the connection mechanism itself (protocol, endpoints, authentication, or logic), and Section 13 of the AGPL-3.0 then applies in full to that code.

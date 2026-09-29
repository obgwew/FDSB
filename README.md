![FDSB](./main_app/icons/FDSB.png)

<p>
  <img src="https://img.shields.io/badge/Version-2.4.2-blue?style=for-the-badge" alt="Version" />
  <img src="https://img.shields.io/badge/Source-AGPL--3.0-blue?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/Languages-10-brightgreen?style=for-the-badge" alt="Languages" />
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
3. Select **New Bot**. On the page that opens, enter the bot token and bot name, and optionally add a bot image.

> [!NOTE]
> In the Discord Developer Portal, create your bot and enable all three Gateway Intents (the toggles at the bottom of the **Bot** tab). Then copy the bot token and paste it into the application.

4. Open the bot and go to **Settings** to select the preferred language and interface theme.

> [!NOTE]
> The bot name and image configured within the application do not modify the original bot on Discord.

> [!WARNING]
> The token is stored locally on the device and is **not encrypted**.

5. Consult the **Wiki** page for the full list of available FDScript commands.
6. Open the **Commands** tab and select the **+** button to create a new command. In the editor, enter a command name (required) and choose a prefix. Write the command's code according to the Wiki, then select **Save**.
7. Return to the main screen and select **Start** to run the bot.

> [!WARNING]
> The application can run in the background, provided that battery optimization is disabled for it and no network restrictions are applied to it.

> [!CAUTION]
> The background-execution settings described above are documented for Android 13 and earlier. Support for Android 14 and later is under development and may be provided in a future update.

---

## Notes

- The built-in command set is intentionally kept simple, while more complex tasks are handled by FDScript. This design choice is unrelated to the number of commands planned for future releases.
- FDScript undergoes gradual changes with each update. Commands may therefore be added, removed, or modified during the Alpha stage. **Sensitive bots should not be built until a stable Beta release is available.**

---

## Versioning Scheme

This project uses its own versioning convention, which differs from Semantic Versioning and other standard schemes. Version numbers follow the format `X.Y.Z`, defined as follows:

| Segment | Incremented when |
|---------|------------------|
| `X.y.z` | A fundamental change is made to how the application receives or sends data, interacts with external intermediaries, or handles automation, exporting, retrieval, and similar behavior. |
| `x.Y.z` | A new feature is introduced, or a usage shortcut or internal automation mechanism becomes permanently dependent on the UI. Also applies when a new language command requires a corresponding UI feature. |
| `x.y.Z` | Bug fixes, additions of FDScript commands, UI corrections or behavioral adjustments, restoration of correct command behavior, and improvements to stability and performance. |

---

## Changelog

**Alpha stage:** 1.0.0 to 2.x.x (current)

### 1.0.0 — Initial Alpha Release
- New interface
- New scripting language: FDScript Gen 0
- New control mechanism

### 1.0.1 — Patch
- Fixed Arabic language rendering
- Fixed translator errors
- Fixed a crash on startup
- Fixed a server connection issue

### 2.0.0 — Feature Update
- Improved UI
- Introduced FDScript Gen 1
- Fixed bot file conflicts
- Added a settings panel
- Added theme support

### 2.0.1 — FDScript Expansion and Fixes
- Added more than 20 new FDScript commands
- Fixed several themes
- Fixed button behavior in `commands_view`
- Fixed inputs in `settings_view`
- Replaced the Kivy icon with the BCFD icon

### 2.1.0 — Task Integration and Event Commands
- Added new administrative commands (basic Discord commands)
- Added new event commands
- Added bot data upload and download
- Began development of FDScript Gen 2
- Fixed several commands

### 2.2.0 — UI Migration to Flet
- Migrated the UI framework from Kivy to Flet
- Updated the UI and added UI effects
- Fixed several UI issues and commands

### 2.2.1 — Fixes and Additional Languages
- Fixed variable commands
- Fixed prefix logic
- Fixed theme switching and language switching
- Added French (Fr) and German (De)

> Following version 2.2.1, the project was officially renamed **FDSB**.

### 2.2.2 — Major Repairs, Languages, and Command View UI
- Fixed additional commands and variables
- Fixed color-coding
- Fixed several UI issues in the command view
- Fixed server issues
- Added Chinese (Zh), Russian (Ru), and Turkish (Tr)

### 2.2.3 — Android-Exclusive Release
- Added APK compatibility
- Fixed several commands
- Improved stability and control responsiveness
- Added more errors to fix later :)

### 2.3.0 — Wiki Page
- Added support for channel commands
- Introduced a new Wiki interface
- Fixed several issues in the command editor
- Fixed text color issues in the Android build

### 2.3.1 — Application Fixes
- Updated the loading screen
- Fixed theme and language issues
- Updated the variables view and the Wiki view
- Fixed several commands

### 2.3.2 — Repairs and Command Support
- Added Polish
- Improved Wiki download speed
- Added HTTP commands
- Added additional split commands
- Fixed further commands and UI issues

### 2.4.0 — New UI, Bot Status, and Additional Commands
- Added all embed commands and further commands
- Added function commands
- Added boost-related events and commands
- Added a button for editing the bot's status
- Fixed HTTP and other commands
- Fixed several UI issues on Android

### 2.4.1 — UI and Command Fixes
- Added menu commands
- Added Persian (Fa-IR) and Urdu (Ur)
- Fixed the UI across all views
- Fixed several commands
- Fixed Android and notification errors

### 2.4.2 — Stability Update (current)
- Added further variable and channel commands
- Began development of FDScript Gen 2.5
- Added UI animations
- Fixed several commands
- Revised the UI and notifications
- Achieved stability on Android 13 and earlier

---

## Contributors

- @y.lw(Hidden for privacy reasons) — Contributor
- [@obgwew](https://github.com/obgwew) — Programming

## Support the Project

[![Sponsor obgwew](https://img.shields.io/badge/Sponsor-obgwew-ea4aaa?style=for-the-badge&logo=github&logoColor=white)](https://github.com/sponsors/obgwew)

---

## License

Copyright (C) 2026 obgwew

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU Affero General Public License** as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
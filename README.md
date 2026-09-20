![FDSB.png](./main_app/icons/FDSB.png)
  <p>
         <img src="https://img.shields.io/badge/Version-2.4.1-blue?style=for-the-badge" alt="Version" />
         <img src="https://img.shields.io/badge/Source-AGPL--3.0-blue?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Status-Alpha-orange?style=for-the-badge" alt="Status" />
</p>


# FDSB - Free Design Studio Bot's

> Build and run Discord bots locally using FDScript — a lightweight, high-level DSL/DSLH specifically designed for this purpose.

---

**Description:** A cross-platform application for creating and running Discord bots locally, using FDScript - a scripting language specifically designed for bot programming - to run your bots as efficiently as possible.

**Goal:** To simplify the process. No hosting required (it runs on-device), no need to write structurally complex code, and no need to deal with any learning or programming limitations – just write a script and get a responsive bot in 30 seconds.

---

# How to use it? 

**APK/EXE**

1. Download the APK/EXE version compatible with your device.

2. You'll see the main interface, which is in English by default.

3. Click the New Bot button to open a page showing two options. Enter your bot token, bot name, and optionally add a bot image.
> [!NOTE]
> On the Discord Developer Portal, create your bot and make sure the three gateway intents (the toggle buttons at the bottom of the Bot tab) are enabled. Then copy your bot's token to paste into the app.

4. Log into the bot and go to Settings to select your preferred language and interface theme.
> [!NOTE]
> The bot's name and image set inside the app do not affect the original bot on Discord.
> [!WARNING]
> The token is stored locally on your device, but it is not encrypted.

5. go to the wiki page, And look for all the commands that pique your curiosity.

6. Go to the Commands tab and click the + button to create a new command. In the editor, enter a name (required) and choose your desired prefix. Write your command's code based on wiki, then click Save when finished.

7. Return to the main interface and press Start to run your bot.
> [!WARNING]
> The application runs in the background, but with the conditions of disabling battery optimization and removing network restrictions imposed on the program.

> [!CAUTION]
> These settings work on Android 13 and below as shown. Regarding Android 14+ or higher, I am still working on providing that; it may be available in future updates. 

---

**Notes:**

- The built-in command set is clearly designed to be deliberately simple, with FDScript handling the more complex tasks. (However, this is not related to the number of commands I plan to add later.)
- While FDScript gen 2 offers greater command-line processing capabilities, it's important to note that some poorly planned complexities may produce undesirable results (please report any such issues).
- FDSceipt It goes through gradual stages of change in each update, so adding/deleting/modifying commands remains guaranteed to happen in the alpha version. (Please do not build sensitive bots until a stable beta release is available.)

---
**Project version numbering system**
- The project's release system follows my own rules for each project update, so it differs from official numbering rules and other such matters.

> Numbering:
  - x.z.z :- This version is customized when there is a radical change in the mechanism for receiving and sending data within the application, dealing with intermediaries outside the application, customized behavior such as automation, exporting, retrieving, and other such matters. 
  - z.x.z :- When a new addition occurs and a shortcut method of use or internal automation mechanisms depend on the UI permanently, or in a special case when adding a new command in the language requires adding a feature in the UI. 
  - z.z.x :- Bug fixes and even the addition of FDScript commands, Fixing some UI errors, changing UI behavior, restoring correct command behavior, and other details such as stability and performance. 


**Changelog:**

  - Alpha: 1.0.0 to 2.x.x(now)

- **1.0.0** — Initial Alpha release
  - New interface
  - New language (FDScript) Gen 0
  - New control mechanism

- **1.0.1** — Patch
  - Fixed Arabic language rendering
  - Fixed translator errors
  - Fixed crash on startup
  - Fixed server connection issue

- **2.0.0** — Feature update
  - Improved UI
  - New FDScript Gen 1
  - Fixed bot file conflicts
  - Added settings panel
  - Added theme support

- **2.0.1** — FDScript Growth & Some Fixes
  - Added 20+ new commands to FDScript
  - Fixed some themes
  - Fixed button behavior in commands_view
  - Fixed inputs in settings_view
  - Replaced Kivy icon with BCFD icon

- **2.1.0** — Task integration & event commands
  - Added new admin commands (Basic Discord commands)
  - Added new event commands
  - Upload/download bot data
  - FDScript gen 2 development
  - Fixed some commands

- **2.2.0** - Upgrade UI By Flet
  - Convert from kivy to flet
  - Ui updated 
  - Ui effects
  - Fixed some ui
  - Fixed some commands

- **2.2.1** - Fixed & Add Languages
  - Fixed vars commands
  - Fixed prefix logical 
  - Fixing theme switching
  - Fix switching languages
  - add 2 languages Fr(French) & De(German)

**After the 2.2.1 update, the project name will officially become FDSB**

- **2.2.2** - Big Repair & Add Languages & Fixed Ui(flet) Command view
  - Fixed more commands & vars
  - Fixed Color-Code
  - Fixed some ui on view command
  - Fixed some ui on view command
  - Fix server
  - add 3 languages ch(chinese) & ru(russian) & tr(turkish)

- **2.2.3** - Exclusive Version For Phones(only Android)
  - APK compatibility
  - Some Fixed commands
  - Increased stability
  - Smooth control
  - add more error to fix Later :)

- **2.2.4** - Update Extensions
  - Added 30+ new commands to FDScript
  - Some Fixed 
  - Various repairs
  - Better stability in the editor

- **2.3.0** - Wiki Page
  - Support for channel commands
  - A new wiki interface 
  - some Fixed in command editor
  - some Fixed the color text on FDSB.apk

- **2.3.1** - Fixed App
  - update the load secren
  - fixed the them and luang
  - update variables view
  - update wiki view
  - some fixed commands

- **2.3.2** - Repair & Command Support
  - add polish languages 
  - fixed speed up download wiki
  - add http commands
  - add more split commands
  - fixed more commands & ui

- **2.4.0** - New UI & Status Bot & more commands
  - add all embed cmds & more cmds 
  - add function commands
  - add evnt & commands for boost
  - new button to edit the bot's status
  - some fixed http & some commands
  - some fixed ui in android
  
- **2.4.1** - fixed ui & commands & more
  - add menu commands
  - add 2 languages Fa-Ir(Farsi) & Ur(Urdu)
  - fixed all views ui
  - some fixed commands
  - some fixed errors of andriod and notifications
  - some fixed commands


---

**Developers:** @y.lw (contributor) · [@obgwew](https://github.com/obgwew) (programming)

---

**Donation:** <iframe src="https://github.com/sponsors/obgwew/card" title="Sponsor obgwew" height="225" width="600" style="border: 0;"></iframe>

---

## License

Copyright (C) 2026 obgwew

This program is free software: you can redistribute it and/or modify
it under the terms of the **GNU Affero General Public License** as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

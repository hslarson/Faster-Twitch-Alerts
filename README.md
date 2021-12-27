# __Faster Twitch Alerts__

<span>
	<img src="https://img.shields.io/maintenance/yes/2021" alt="maintenance status" />
	<img src="https://img.shields.io/github/last-commit/hslarson/Faster-Twitch-Alerts" alt="github last commit" />
	<img src="https://img.shields.io/github/issues/hslarson/Faster-Twitch-Alerts" alt="github issues">
	<img src="https://img.shields.io/github/license/hslarson/Faster-Twitch-Alerts" alt="github license" />
</span>
<hr>


## __What is "Faster Twitch Alerts"?__
Faster Twitch Alerts is a highly customizable, lightning-fast alternative to Twitch's slow mobile notification system. Faster Twitch Alerts currently supports two notification platforms: Discord and Pushover.
<br><br>

The program can notify you when:
- A streamer goes live
- A streamer goes offline
- A streamer gets banned
- A streamer is unbanned
- A streamer updates their title and/or game
<br><br>

Disclaimer: This program is not associated in any way with Twitch, Discord, or Pushover
<hr>


## __Getting Started__
1. Clone the repository
2. Install the Python 3 and the Python requests library
3. Set your notification preferences in the [config.json File](#config-fields-explained)
4. Run Main.py
    - If the program terminates unexpectedly, check the log file for more information
    - You can terminate the program at any time using 'ctrl+c'
<hr>


## __Config Fields Explained__


### Primary Fields
For more detailed explanations of each field, follow the links

| Field Name                              | Required? |
|-----------------------------------------|-----------|
| [Twitch Settings](#twitch-settings)     | Yes       |
| [Logger Settings](#logger-settings)     | Yes       |
| [Streamers](#streamers)                 | Yes       |
| [Discord Settings](#discord-settings)   | No        |
| [Pushover Settings](#pushover-settings) | No        |
<br>

### Twitch Settings
This is where we store overall program settings and settings related to the Twitch API
<br><br>

#### __Example Twitch Settings Object:__

```
"Twitch Settings" : {
	"Client ID" : "YOUR CLIENT ID",
	"Secret" : "YOUR SECRET",
	"Reconnect Attempts" : 10,
	"Reconnect Cooldown" : 60,
	"Refresh Rate" : 1
}
```
<br>

#### __Twitch Settings Fields:__
| Field Name | Description | Required? | Datatypes | [Alert-Specific Settings](#alert-specific-settings) | [Special Formatting](#special-formatting) |
| - | - | - | - | - | - |
| Client ID | Your Twitch developer application client ID <sup>1</sup> | Yes | str | Not Allowed | Not Allowed |
| Secret | Your Twitch developer application client secret <sup>1</sup> | Yes | str | Not Allowed | Not Allowed |
| Reconnect Attempts | The number of times the program will attempt to reconnect to the network during an outage <sup>2</sup> | Yes | int | Not Allowed | Not Allowed |
| Reconnect Cooldown | The amount of time (in seconds) that the program will wait before trying to reconnect to the network after a connection failure |Yes | int, float | Not Allowed | Not Allowed |
| Refresh Rate<sup>3</sup> | The number of times per second to pull new data from the Twitch API | Yes | int, float | Not Allowed | Not Allowed |

__Footnotes:__
- <sup>1</sup> [Setting Up a Twitch Developer Application](https://dev.twitch.tv/docs/api/)
- <sup>2</sup> Negative values signal infinite reconnect attempts
- <sup>3</sup> There is a hard cap on the refresh rate imposed by Twitch API rate limits. You can calculate the refresh rate using the following formula: 20 / (3 * ceil( [# of streamers] / 100 ))
<br><br>



### Logger Settings
Settings related to the log file
<br><br>

#### __Example Logger Settings Object:__
```
"Logger Settings" : {
	"Log Level" : "INFO",
	"Log Filepath" : "logs/twitch_alerts.log",
	"Message Text" : "ALERT!"
}
```
<br>

#### __Logger Settings Fields:__
| Field Name | Description | Required? | Datatypes | [Alert-Specific Settings](#alert-specific-settings) | [Special Formatting](#special-formatting) |
| - | - | - | - | - | - |
| Log Level | Allows users to define which messages they receive <sup>1</sup> | Yes | str | Not Allowed | Not Allowed |
| Log Filepath | The path (relative to current working directory) of the log file | Yes | str | Not Allowed | Not Allowed |
| Message Text | Text to display when an [alert](#alert-types) is triggered | No <sup>2</sup> | str | Allowed | Allowed |

__Footnotes:__
- <sup>1</sup> More Info on Log Levels:
	- DEBUG: Shows minor network errors
	- INFO: Info about streamer activity, and general program info
	- WARNING: Info about non-fatal errors
	- ERROR: Info about fatal errors
- <sup>2</sup> A warning will be displayed if field is incomplete and log level is either DEBUG or INFO
<br><br>



### Streamers
The JSON object containing settings for all of the streamers we wish to monitor
<br><br>

#### __Example Streamers Object__:
```
"Streamers" : {
	"streamer-username-1" : {
		"Ban Status" : false,
		"User ID" : "123456789"
	},
	"streamer-username-2" : {
		"Ban Status" : true,
		"User ID" : "987654321"
	}
}
```
<br>

#### __Streamer Object Fields:__
| Field Name | Description | Required? | Datatypes | [Alert-Specific Settings](#alert-specific-settings) | [Special Formatting](#special-formatting) |
| - | - | - | - | - | - |
| Ban Status | A Boolean flag used to signal if a streamer is banned <sup>1</sup> | Yes | bool | Not Allowed | Not Allowed |
| User ID | A streamer's unique identification number (provided by Twitch) <sup>1</sup> | Yes | str | Not Allowed | Not Allowed |
| Discord Settings | Streamer-Specific Discord Settings. For possible fields see [Discord Settings](#discord-settings) <sup>2</sup> | No | dict | N/A | N/A |
| Pushover Settings | Streamer-Specific Pushover Settings. For possible fields see [Pushover Settings](#pushover-settings) <sup>2</sup> | No | dict | N/A | N/A |

__Footnotes:__
- <sup>1</sup> A streamer's user ID can only be viewed using API calls, it is recommended that you use the set_config.py program in Utils/ to generate the "Streamers" field
- <sup>2</sup> The "Soon Cooldown" field can only exist in global settings
<br><br>

#### __Sidenote: Global vs. Streamer-Specific Settings__
We refer to Discord/Pushover settings within the streamer object as "streamer-specific settings." These settings take precedence over "global settings" in either [Discord Settings](#discord-settings) or [Pushover settings](#pushover-settings). In this way, we can create global settings that will apply to all streamers, and also make fine-grain adjustments to individual streamers' settings.
<br><br>



### Discord Settings
Global settings for Discord alerts
<br><br>

#### __Example Discord Settings Object:__
```
"Discord Settings" : {
	"Soon Cooldown" : 300,
	"Alerts" : "all",
	"Webhook URL" : "SOME WEBHOOK URL",
	"Bot Username" : "Faster Twitch Alerts",
	"Avatar URL" :   "Link to Avatar Image",
	"Discord ID" :   "Some Discord ID",
	"Message Text" : "DISCORD ALERT!"
}
```
<br>

#### __Example Discord Settings Fields:__
| Field Name | Description | Required? | Datatypes | [Alert-Specific Settings](#alert-specific-settings) | [Special Formatting](#special-formatting) |
| - | - | - | - | - | - |
| Soon Cooldown | Controls how often changes to an individual streamer's title or game will generate an alert by setting a cooldown period (units = seconds) | Yes | int, float | Not Allowed | Not Allowed |
| [Alerts](#alerts-field) | Controls what types of messages will generate an alert | No | str | Allowed | Not Allowed |
| Webhook URL | The Webhook URL for the Discord channel which will receive the alert | No<sup>1</sup> | str | Allowed | Allowed |
| Bot Username | The display name of the bot that will be the sender of the alert | No | str | Allowed | Allowed |
| Avatar URL | A direct link to an image that will be the Discord bot's avatar | No | str | Allowed | Allowed |
| Discord ID<sup>2</sup> | A Discord role/user ID that can be used to tag members of a Discord server. See below for examples | No | str | Allowed | Allowed |
| Message Text | Text to display when an [alert](#alert-types) is triggered | No<sup>1</sup> | str | Allowed | Allowed |

__Footnotes:__
- <sup>1</sup> These fields must be defined for all active alert types in either global settings or streamer-specific settings otherwise the program will terminate
- <sup>2</sup> You can find user/role ID's by activating "Developer Mode" on Discord
<br><br>

__Discord Message Tips:__

Mentions:
```
Users: "<@discord_id>"
Roles: "<@&discord_id>"
```
<br>

Using a Custom Server Emoji:
```
Normal:    "<:emoji_alias:emoji_id>"
Animated: "<a:emoji_alias:emoji_id>"
```
<br><br>



### Pushover Settings
Global settings for Pushover alerts
<br><br>

#### __Example Pushover Settings Object:__
```
"Pushover Settings" : {
	"Soon Cooldown" : 300,
	"Alerts" : "all",
	"API Token" : "YOUR API TOKEN",
	"Group Key" : "YOUR GROUP KEY",
	"Devices" : "Some Devices",
	"Priority" : 1,
	"Embed URL" : "https://www.twitch.tv/{name.lower()}",
	"URL Title" : "Go To Stream",
	"Sound" : "Some Sound",
	"Message Title" : "Faster Twitch Alerts",
	"Message Text" : {
		"live" : "{name} is Live Right Now! \ud83d\udce1",
		"title" : "{name} Might Be Going Live Soon! \u231b",
		"game" : "{name} Might Be Going Live Soon! \u231b",
		"offline" : "{name} Just Went Offline \ud83d\ude14",
		"ban" : "{name} Just Got Banned \u2696\ufe0f",
		"unban" : "{name} has Been Unbanned! \ud83c\udf89"
	}
}
```
<br>

#### __Example Pushover Settings Fields:__
| Field Name | Description | Required? | Datatypes | [Alert-Specific Settings](#alert-specific-settings) | [Special Formatting](#special-formatting) |
| - | - | - | - | - | - |
| Soon Cooldown | Controls how often changes to an individual streamer's title or game will generate an alert by setting a cooldown period (units = seconds) | Yes | int, float | Not Allowed | Not Allowed |
| [Alerts](#alerts-field) | Controls what types of messages will generate an alert | No | str | Allowed | Not Allowed |
| API Token<sup>1</sup> | Pushover API token | No<sup>2</sup> | str | Allowed | Allowed |
| Group Key<sup>1</sup> | Pushover User or Group Key | No<sup>2</sup> | str | Allowed | Allowed |
| Devices<sup>1</sup> | Comma-separated list of device names to send the alert to | No | str | Allowed | Allowed |
| Priority<sup>1</sup> | Integer from -2 to 2 that specifies how important the alert is | No | int | Allowed | Not Allowed |
| Embed URL<sup>1</sup> | Supplementary URL for the alert | No | str | Allowed | Allowed |
| URL Title<sup>1</sup> | The text to display for the "Embed URL" | No | str | Allowed | Allowed |
| Sound<sup>1</sup> | The name of the sound to play for the alert | No | str | Allowed | Allowed |
| Message Title<sup>1</sup> | The title of the alert | No | str | Allowed | Allowed |
| Message Text | Text to display when an [alert](#alert-types) is triggered | No<sup>2</sup> | str | Allowed | Allowed |

__Footnotes:__
- <sup>1</sup> [More information about Pushover alert fields](https://pushover.net/api)
- <sup>2</sup> These fields must be defined for all active alert types in either global settings or streamer-specific settings otherwise the program will terminate
<hr><br>



## Alert-Specific Settings
For certain fields, we may want to change our preferences based on the [type of alert](#alert-types) being triggered. This is fairly easy to do, we can simply create a JSON object of [alert-type keywords](#alert-types) and specify different parameters for each keyword.
<br><br>

#### __Alert-Specific Settings Example:__
Without Alert-Specific Settings:
```
"Message Text" : "Some Alert Message"
```

With Alert-Specific Settings:
```
"Message Text" : {
	"live"    : "Some 'Live' Message",
	"offline" : "Some 'Offline' Message",
	"ban"     : "Some 'Ban' Message",
	"unban"   : "Some 'Unban' Message",
	"title"   : "Some 'Title Change' Message",
	"game"    : "Some 'Game Change' Message"
}
```
<br>

### __Alert Types__
Faster Twitch Alerts can send alerts for many types of events. Below are the keywords describing each alert type

| Alert Type | Description |
| - | - |
| live | The streamer went live |
| offline | The streamer went offline |
| ban | The streamer was banned |
| unban | The streamer's ban ended |
| title | The streamer updated their stream's title (while offline) |
| game | The streamer switched categories (while offline) |
<br>

### __Keyword Mapping__
For the sake of efficiency, we've provided additional keywords that specify multiple alert fields. Below you can see the keywords and which alert types they map to.

| Alert Type | Description |
| - | - |
| all | live, offline, ban, unban, title, game |
| none<sup>1</sup> |  |
| bans | ban, unban |
| soon | title, game |

__Footnotes:__
- <sup>1</sup> Only valid for the ["Alerts" field](#alerts-field)
<br><br>

### __Alerts Field__
The Alerts field is used to toggle certain alert types on and off.

__Valid "Alerts" Formats:__

Boolean Keyword Dictionary:
```
"Alerts" : {
	"live"    : true
	"offline" : true,
	"ban"     : true,
	"unban"   : true,
	"title"   : true,
	"game"    : true
}
```
		
Comma-Separated Keywords in String Format:
```
"Alerts" : "live, offline, ban, unban, title, game"
```

__Negation Operator:__

'!' Can be used in front of a keyword to negate that keyword

Note that keywords are parsed in order, for example
- "all, !live" -> Alerts for everything except "live"
- "!live, all" -> Alerts for everything, even "live"
<hr><br>



## Special Formatting
Sometimes we want more customization beyond what a normal string can offer. For this reason we've created a special formatting system for certain fields.
<br><br>

__Here's how it works:__

Every statement in curly braces will be evaluated by the formatter. The formatter understands Python and expects a string to be returned by whatever is contained in the braces.
<br><br>

There are a few local variables we can use as well. These fields will change depending on the alert type and the streamer.
| Variable | Description |
| - | - |
| time | Evaluates to time.localtime() |
| name | The username of the streamer |
| title | The streamer's current stream title |
| game | The streamer's current game category |
| message | The [alert type](#alert-types) of the message |
| discord_id | The user-specified Discord ID for the message |
<br>

Due to the way Python interprets strings, we may need alternate ways to specify escape characters. Below are the currently available alternatives
| Variable | Description |
| - | - |
| nl | newline |
| tb | tab |
| dq | double quote |
| sq | single quote |
<br>

__Examples:__

Basic Example:
```
"Message Text" : {
	"ban" : "{name} Was Just Banned",
	"unban" : "{name} Was Just Unbanned",
	"live" : "{name} Just Went Live",
	"offline" : "{name} Just Went Offline",
	"title" : "{name} Changed Their Title to \"{title}\"",
	"game" : "{name} Changed Their Game to \"{game}\""
}
```
<br>

String Formatting Example:
```
"Bot Username" : "{name.capitalize()} - {message.capitalize()}"
```
<br>

If/Else Statement Example:
```
"Message Text" : {
	"bans" : "{name} Was Just {'Ban' if message=='ban' else 'Unban'}ned"
}
```
<br>

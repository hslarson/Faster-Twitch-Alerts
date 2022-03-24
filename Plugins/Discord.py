from Validate import check_keys, ALERT_TYPES
from Exceptions import ConfigFormatError
from Notifications import Notifications
from Config import Config
import time


# A Class for Constructing Discord Notifications
class Discord():

	# Config File Key With Plugin's Settings
	SETTINGS_KEY = "Discord Settings"


	# Makes Sure that the Plugin Settings Given in the Config File Are Valid
	# Pre-Condition: Config File Has Been Loaded
	# Post-Condition: An Error Was Triggered or Warnings (if any) Have Been Returned
	def validate():

		# Recognized Settings
		KEYS = {
			"Soon Cooldown" : {float, int},
			"Alerts"        : {str, (dict,bool)},
			"Bot Username"  : {str, (dict,str)},
			"Avatar URL"    : {str, (dict,str)},
			"Webhook URL"   : {str, (dict,str)},
			"Message Text"  : {str, (dict,str)},
			"Discord ID"    : {str, (dict,str)},
			"Embeds"        : {(list,dict), (dict,list,dict)}
		}

		# Check Key Datatypes
		warnings = check_keys(Discord.SETTINGS_KEY, Config.config_file[Discord.SETTINGS_KEY],optional_keys=KEYS)
		global_settings = Config.parse_preferences("GLOBAL", Discord)

		for streamer in Config.config_file["Streamers"]:
			streamer_settings = Config.parse_preferences(streamer, Discord)

			# Check Datatypes for Streamer-Specific Settings
			warnings += check_keys(Discord.SETTINGS_KEY + "/" + streamer, streamer_settings, optional_keys=KEYS)

			# Do a Dry-Run of Alerts
			for alert in ALERT_TYPES :
				if not Notifications.preference_resolver("Alerts", alert, global_settings, streamer_settings): continue

				# Check for Webhook URL
				if Notifications.preference_resolver("Webhook URL", alert, global_settings, streamer_settings) == None:
					raise ConfigFormatError("Discord Alert Dry-Run Failed: Streamer=" + streamer + ". Message=" + alert + ". Missing Field=Webhook URL")
				
				# Check Embeds
				embeds = Notifications.preference_resolver("Embeds", alert, global_settings, streamer_settings)
				if embeds != None:
					if not len(embeds):
						raise ConfigFormatError("Discord Alert Dry-Run Failed: Streamer=" + streamer + ". Message=" + alert + ". Empty Embeds Field")

					for embed in embeds:
						if type(embed) != dict:
							raise ConfigFormatError("Discord Alert Dry-Run Failed: Streamer=" + streamer + ". Message=" + alert + ". Found Non-Dictionary Embed")

				# Raise Error if Neither Message Text Nor Embeds Were Specified
				elif Notifications.preference_resolver("Message Text", alert, global_settings, streamer_settings) == None:
					raise ConfigFormatError("Discord Alert Dry-Run Failed: Streamer=" + streamer + ". Message=" + alert + ". Need At Least One of 'Message Text' or 'Embeds'")
		
		return warnings



	# Initialize Module
	# Pre-Condition: Streamer Dict. Has Been Generated and Discord Module Has Been Enabled in Config File
	def init(streamer_dict):

		# Parse Global Settings
		Discord.GLOBAL_SETTINGS = Config.parse_preferences("GLOBAL", Discord)

		# Generate Streamer Settings
		for user in streamer_dict:
			streamer_dict[user].module_preferences["Discord"] = Config.parse_preferences(user, Discord)
			streamer_dict[user].module_last_change["Discord"] = 0



	# Generate a Discord Notification
	# Pre-Condition: An Alert Has Been Generated
	# Post-Condition: A Valid Notification Payload Has Been Sent to Notifications.send()
	async def alert(streamer_obj, message):

		# Don't Send Messages That the User Doesn't Want
		if not Notifications.preference_resolver("Alerts", message, Discord.GLOBAL_SETTINGS, streamer_obj.module_preferences["Discord"]):
			return

		# Check & Reset the Soon Cooldown if Needed
		elif message == "title" or message == "game":
			
			cooldown = Notifications.preference_resolver("Soon Cooldown", message, Discord.GLOBAL_SETTINGS, streamer_obj.module_preferences["Discord"])
			cooldown = float(cooldown) if cooldown != None else 0
			
			if time.time() > streamer_obj.module_last_change["Discord"] + cooldown:
				streamer_obj.module_last_change["Discord"] = time.time()
			else:
				return

		# Resolve User Preferences
		preferences = {}
		for keyword in ("Discord ID", "Message Text", "Webhook URL", "Bot Username", "Avatar URL"):
			preferences[keyword] = Notifications.preference_resolver(keyword, message, Discord.GLOBAL_SETTINGS, streamer_obj.module_preferences["Discord"])

		# Format Preferences
		for pref in ("Discord ID", "Message Text", "Webhook URL", "Bot Username", "Avatar URL"):
			if preferences[pref] != None:
				preferences[pref] = Notifications.special_format(
					str(preferences[pref]),

					name  = streamer_obj.name,
					title = streamer_obj.last_title,
					game  = streamer_obj.last_game,
					message = str(message),
					discord_id = "[Null ID]" if preferences["Discord ID"] == None else preferences["Discord ID"]
				)

		# Format Embeds
		# We Have to Hard Copy the Embed List so it looks a Bit Messy
		embed_pref = Notifications.preference_resolver("Embeds", message, Discord.GLOBAL_SETTINGS, streamer_obj.module_preferences["Discord"])
		if embed_pref != None:
			out = []
			for embed in embed_pref:
				temp_dict = {}
				for key in embed:
					if type(embed[key]) != str:
						temp_dict[key] = embed[key]
						continue
					
					temp_dict[key] = Notifications.special_format(
						embed[key],

						name  = streamer_obj.name,
						title = streamer_obj.last_title,
						game  = streamer_obj.last_game,
						message = str(message),
						discord_id = "[Null ID]" if preferences["Discord ID"] == None else preferences["Discord ID"]
					)
				out.append(temp_dict)
			preferences["Embeds"] = out
		else: preferences["Embeds"] = None
		
		# Construct Body
		data = {
			"allowed_mentions": {
				"parse": ["everyone"]
			}
		}

		for config_key, req_param in {
			("Message Text", "content"),
			("Bot Username", "username"),
			("Avatar URL", "avatar_url"),
			("Embeds", "embeds")
		}:
			if preferences[config_key] != None:
				data[req_param] = preferences[config_key]

		# Send Message to Discord
		coro = Notifications.requests.post(preferences["Webhook URL"], json=data, timeout=10)
		await Notifications.send(coro)

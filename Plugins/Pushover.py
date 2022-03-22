from Validate import check_keys, ALERT_TYPES
from Exceptions import ConfigFormatError
from Notifications import Notifications
from Config import Config
import time


# A Class for Constructing Pushover Notifications
class Pushover():

	SETTINGS_KEY = "Pushover Settings"


	# Makes Sure that the Plugin Settings Given in the Config File Are Valid
	# Pre-Condition: Config File Has Been Loaded
	# Post-Condition: An Error Was Triggered or Warnings (if any) Have Been Returned
	def validate():
		
		# Recognized Settings
		KEYS = {
			"Soon Cooldown" : {float, int},
			"Alerts"        : {str, (dict,bool)},
			"API Token"     : {str, (dict,str)},
			"Group Key"     : {str, (dict,str)},
			"Embed URL"     : {str, (dict,str)},
			"Priority"      : {int, (dict,int)},
			"Devices"       : {str, (dict,str)},
			"URL Title"     : {str, (dict,str)},
			"Message Text"  : {str, (dict,str)},
			"Message Title" : {str, (dict,str)},
			"Sound"         : {str, (dict,str)}
		}

		# Check Key Datatypes
		warnings = check_keys(Pushover.SETTINGS_KEY, Config.config_file[Pushover.SETTINGS_KEY], optional_keys=KEYS)
		global_settings = Config.parse_preferences("GLOBAL", Pushover)

		for streamer in Config.config_file["Streamers"]:
			streamer_settings = Config.parse_preferences(streamer, Pushover)

			# Check Datatypes for Streamer-Specific Settings
			warnings += check_keys(Pushover.SETTINGS_KEY + "/" + streamer, streamer_settings, optional_keys=KEYS)

			# Do a Dry-Run of Alerts
			for alert in ALERT_TYPES :
				if not Notifications.preference_resolver("Alerts", alert, global_settings, streamer_settings): continue

				# Make Sure All Required Fields Are Present
				for item in {"API Token", "Group Key", "Message Text"}:
					if Notifications.preference_resolver(item, alert, global_settings, streamer_settings) == None:
						raise ConfigFormatError("Pushover Alert Dry-Run Failed: Streamer=" + streamer + ". Message=" + alert + ". Missing Field=" + item)
		
		return warnings	



	# Initialize Module
	# Pre-Condition: Streamer Dict. Has Been Generated and Pushover Module Has Been Enabled in Config File
	def init(streamer_dict):

		# Generate Global Settings
		Pushover.GLOBAL_SETTINGS = Config.parse_preferences("GLOBAL", Pushover)

		# Generate Streamer Settings
		for user in streamer_dict:

			streamer_dict[user].module_preferences["Pushover"] = Config.parse_preferences(user, Pushover)
			streamer_dict[user].module_last_change["Pushover"] = 0



	# Generate a Pushover Notification
	# Pre-Condition: An Alert Has Been Generated
	# Post-Condition: A Valid Notification Payload Has Been Sent to Notifications.send()
	async def alert(streamer_obj, message):

		# Don't Send Messages That the User Doesn't Want
		if not Notifications.preference_resolver("Alerts", message, Pushover.GLOBAL_SETTINGS, streamer_obj.module_preferences["Pushover"]):
			return

		# Check & Reset the Soon Cooldown if Needed
		elif message == "title" or message == "game":
			
			cooldown = Notifications.preference_resolver("Soon Cooldown", message, Pushover.GLOBAL_SETTINGS, streamer_obj.module_preferences["Pushover"])
			cooldown = float(cooldown) if cooldown != None else 0
			
			if time.time() > streamer_obj.module_last_change["Pushover"] + cooldown:
				streamer_obj.module_last_change["Pushover"] = time.time()
			else:
				return

		# Get User Preferences
		preferences = {}
		for keyword in ("Message Text", "API Token", "Group Key", "Embed URL", "URL Title", "Devices", "Message Title", "Priority", "Sound"):
			preferences[keyword] = Notifications.preference_resolver(keyword, message, Pushover.GLOBAL_SETTINGS, streamer_obj.module_preferences["Pushover"])

			# Format Message and Bot Username
			if preferences[keyword] != None and type(preferences[keyword]) == str:
				preferences[keyword] = Notifications.special_format(
					preferences[keyword],

					name  = streamer_obj.name,
					title = streamer_obj.last_title,
					game  = streamer_obj.last_game,
					message = str(message)
				)
			
		# Construct Message
		payload = {
			'token' : preferences["API Token"],
			'user' :  preferences["Group Key"],
			'message' :	preferences["Message Text"]
		}

		# Add Optional Parameters
		for pref, index in (
			("Embed URL", "url"),
			("URL Title", "url_title"),
			("Devices", "device"),
			("Message Title", "title"),
			("Priority", "priority"),
			("Sound", "sound")
		):
			if preferences[pref] != None:
				payload[index] = preferences[pref]

		# Send Message to Pushover
		coro = Notifications.requests.post("https://api.pushover.net/1/messages.json", json=payload, timeout=10)
		await Notifications.send(coro)

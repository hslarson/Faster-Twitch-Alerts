from Notifications import Notifications
from Config import Config
import time


class Pushover():

	# Initialize Module
	# Pre-Condition: Streamer Dict. Has Been Generated and Pushover Module Has Been Enabled in Config File
	def init(streamer_dict):

		# Incorperate Pushover Into Notifications Module
		Notifications.pushover = Pushover.pushover
		Notifications.PUSHOVER = 4

		# Generate Global Settings
		Notifications.PUSHOVER_GLOBAL_SETTINGS = Config.parse_preferences("GLOBAL", "Pushover")

		# Generate Streamer Settings
		for user in streamer_dict:

			streamer_dict[user].module_preferences["Pushover"] = Config.parse_preferences(user, "Pushover")
			streamer_dict[user].module_last_change["Pushover"] = 0



	# Generate a Pushover Notification
	# Pre-Condition: An Alert Has Been Generated
	# Post-Condition: A Valid Notification Payload Has Been Sent to Notifications.send()
	async def pushover(streamer_obj, message):

		# Don't Send Messages That the User Doesn't Want
		if not Notifications.preference_resolver("Alerts", message, Notifications.PUSHOVER_GLOBAL_SETTINGS, streamer_obj.module_preferences["Pushover"]):
			return

		# Check & Reset the Soon Cooldown if Needed
		elif message == "title" or message == "game":
			
			cooldown = Notifications.PUSHOVER_GLOBAL_SETTINGS["Soon Cooldown"]
			if time.time() > streamer_obj.module_last_change["Pushover"] + cooldown:
				streamer_obj.module_last_change["Pushover"] = time.time()
			else:
				return

		# Get User Preferences
		preferences = {}
		for keyword in ("Message Text", "API Token", "Group Key", "Embed URL", "URL Title", "Devices", "Message Title", "Priority", "Sound"):
			preferences[keyword] = Notifications.preference_resolver(keyword, message, Notifications.PUSHOVER_GLOBAL_SETTINGS, streamer_obj.module_preferences["Pushover"])

		# Format Message and Bot Username
		for pref in ("Message Text", "API Token", "Group Key", "Embed URL", "URL Title", "Devices", "Message Title", "Sound"):
			if preferences[pref] != None:
				preferences[pref] = Notifications.special_format(
					str(preferences[pref]),

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
		await Notifications.send("https://api.pushover.net/1/messages.json", Notifications.PUSHOVER, payload)
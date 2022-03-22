from Exceptions import ConfigFileError
from Validate import is_alert_specific
import asyncio
import json
import os


# The Config Class Handles All Operations Related to the config.json File, Including Loading, Parsing, Altering, and Saving
class Config():

	enabled_modules = []
	file_lock = asyncio.Lock()


	# Loads the config file and stores it in a dictionary
	# Post-Condition: Config File Has Been Loaded into Config.config_file if No Syntax Errors Have Been Found
	async def load():

		await Config.file_lock.acquire()
		try:
			# Generate filepath
			dirname = os.path.dirname(__file__)
			Config.filename = os.path.join(dirname, 'config.json')

			# Open the file and save it
			file = open(Config.filename, 'r')
			Config.config_file = json.load(file)

			file.close()
			Config.file_lock.release()

		# Handle Exceptions
		except (KeyboardInterrupt, GeneratorExit):
			raise
		except BaseException as err:
			raise ConfigFileError(err)



	# Dumps the Contents of Config.config_file Back into the Original Config File
	# Pre-Condition: Config.config_file Contains the Updated Contents of config.json
	# Post-Condition: The Contents of Config.config_file Have Been Saved in config.json
	async def save():

		# Try to dump the updated config_file into the config.json
		await Config.file_lock.acquire()
		try:
			file = open(Config.filename, "w")
			json.dump(Config.config_file, file, indent='\t', separators=(',',' : '))

			file.close()
			Config.file_lock.release()

		# Handle Exceptions
		except (KeyboardInterrupt, GeneratorExit):
			raise
		except BaseException as err:
			raise ConfigFileError(err)



	# Used By Streamer.py to Alter a Streamer's Ban Status in the Config File
	async def update_ban_status(streamer, status):

		# Reload the config file before altering it
		await Config.load()

		# Update the Config JSON
		if streamer in Config.config_file["Streamers"]:
			Config.config_file["Streamers"][streamer]["Ban Status"] = status

		# Save the JSON
		await Config.save()



	# Used By TwitchAPI.__check_username() to Update Streamer Usernames that May Have Changed
	# Post-Condition: The Streamer's Entry in the Streamer Dictionary has Been Updated Without Changing the Order
	async def update_username(old_name, new_name):

		# Reload the config file before altering it
		await Config.load()

		# Separate Key/Value Pairs into Lists
		keys = list(Config.config_file["Streamers"].keys())
		vals = list(Config.config_file["Streamers"].values())

		# Replace the Old Key With the New One
		if old_name in keys:
			keys[ keys.index(old_name) ] = new_name

		# Create a New Dict. From the Key/Value Lists
		temp_dict = {}
		for index, name in enumerate(keys):
			temp_dict[name] = vals[index]

		# Replace Old Dictionary With New One
		Config.config_file["Streamers"] = temp_dict

		# Save the JSON
		await Config.save()



	# A General Function For Parsing Global and Streamer-Specific Settings From the Config File
	# Pre-Condition: A Valid Settings Parameter Has Been Provided in the Config File
	# Post-Condition: A Dictionary of Settings Has Been Returned
	def parse_preferences(streamer, service):
		out = {}

		# If Service is Disabled, Disable All Notifications
		if (streamer != "GLOBAL" and service not in Config.enabled_modules) or not hasattr(service, 'SETTINGS_KEY'):
			return out

		# Load All Settings for Service
		if streamer == "GLOBAL":
			settings = Config.config_file[service.SETTINGS_KEY]
		elif service.SETTINGS_KEY in Config.config_file["Streamers"][streamer]:
			settings = Config.config_file["Streamers"][streamer][service.SETTINGS_KEY]
		else:
			return out

		# Add Everything But Alerts to Out
		Config.parse_settings(out, settings)

		# Save Alert Settings, or Just Return
		if "Alerts" in settings:
			Config.parse_alerts(out, settings["Alerts"], streamer=="GLOBAL")

		return out



	# Helper Function For parse_preferences() Used to Expand Keywords
	# Pre-Condition: A Valid Settings Dictionary Has Been Provided in the Config File
	# Post-Condition: All Settings Fields in Dictionary Form Have Had Their Keywords Expanded
	def parse_settings(out, settings):

		# Cycle through settings
		for item in settings:

			# Ignore alerts, there's a dedicated function for that
			if item == "Alerts":
				continue

			# If the user specifies message-specific settings, decode them
			if is_alert_specific(settings[item]):	

				out[item] = {}
				for key in settings[item]:
					val = settings[item][key]
					key = key.lower()

					# Expand Special Keywords
					# Program expands 'all' so other alert types can overwrite settings
					if key == "all":
						for k in {"live", "title", "game", "offline", "ban", "unban"}: out[item][k] = val
					elif key == "bans":
						out[item]["ban"] = out[item]["unban"] = val
					elif key == "soon":
						out[item]["title"] = out[item]["game"] = val

					# Handle Normal Keywords
					elif key.lower() in {"live", "title", "game", "offline", "ban", "unban"}:
						out[item][key] = val

			# Handle general settings
			else:	
				out[item] = settings[item] # Note that we aren't validating datatypes in this function



	# Helper Function for parse_preferences() Used to Parse "Alerts" Key in Config File
	# Pre-Condition: A valid "Alerts" parameter has been provided in the config file
	# Post-Condition: A dictionary has been created with boolean values indicating the appropriate alert settings
	# 	- If the defaults flag is True, we are generating global settings, meaning that each of the alert fields will be filled (False unless otherwise specified)
	#	- If the defaults flag is False, we are generating streamer-specific settings, meaning that a partial dictionary is possible. Any unspecified fields will be filled with global defaults later
	def parse_alerts(out, alert_settings, defaults=False):

		# Add Alerts to Out Dict.
		out["Alerts"] = {}

		# Fill the Default Dict. With False for All Fields
		ALERT_FIELDS = ("live", "title", "game", "offline", "ban", "unban")
		if defaults:
			for field in ALERT_FIELDS: out["Alerts"][field] = False

		# Handle Alerts in String Form
		if type(alert_settings) == str:

			# Split String and Generate Array
			temp = [x.strip() for x in alert_settings.split(sep=',')]

			# Transform List to Dict.
			alert_settings = {}
			for alert_type in temp:
				alert_settings[alert_type] = True

		# Handle the Dict.
		for field in alert_settings:

			# Save Alert Type and Setting
			alert_type = field.lower()
			setting = alert_settings[field]

			# Handle Negation Operator
			if alert_type[0] == '!':
				alert_type = alert_type[1:]
				setting = not setting

			# Expand Special Keywords
			if alert_type == "all":
				for f in ALERT_FIELDS: out["Alerts"][f] = setting

			elif alert_type == "none":
				for f in ALERT_FIELDS: out["Alerts"][f] = not setting
	
			elif alert_type == "soon":
				out["Alerts"]["title"] = setting
				out["Alerts"]["game"] = setting

			elif alert_type == "bans":
				out["Alerts"]["ban"] = setting
				out["Alerts"]["unban"] = setting

			# Handle Normal Keywords
			else:
				out["Alerts"][alert_type] = setting

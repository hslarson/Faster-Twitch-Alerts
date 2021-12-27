from Exceptions import ConfigFileError
import asyncio
import json
import os


# The Config Class Handles All Operations Related to the config.json File, Indcluding Loading, Parsing, Altering, and Saving
class Config():

	enabled_modules = set()
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



	# Helper Function for parse_preferences() Used to Parse "Alerts" Key in Config File
	# Pre-Condition: A valid "Alerts" parameter has been provided in the config file
	# Post-Condition: A dictionary has been created with boolean values indicating the appropriate alert settings
	# 	- If the defualts flag is True, we are generting global settings, meaning that each of the alert fields will be filled (False unless otherwise specified)
	#	- If the defaults flag is False, we are generating streamer-specific settings, meaning that a partial dictionary is possible. Any unspecified fields will be filled with global defaults later
	def __parse_alerts(out, alert_settings, defaults=False):

		# Add Alerts to Out Dict.
		out["Alerts"] = {}
		
		# Fill the Defult Dict. With False for All Fields
		ALERT_FIELDS = ("live", "title", "game", "offline", "ban", "unban")
		if defaults:
			for field in ALERT_FIELDS: out["Alerts"][field] = False

		# Handle Alerts in String Form
		if type(alert_settings) != dict:
			
			# Split String and Generate Array
			if type(alert_settings) == str:
				temp = [x.strip() for x in alert_settings.split(sep=',')]
			
				# Transform List to Dict.
				alert_settings = {}
				for alert_type in temp:
					alert_settings[str(alert_type)] = True

		# Handle the Array
		for field in alert_settings:
			
			# Save Alert Type and Setting
			alert_type = str(field).lower()
			setting = alert_settings[field]
			
			# Handle Negation Operator
			if alert_type[0] == '!':
				alert_type = alert_type[1:]
				setting = not setting

			# Handle General Key-phrases
			elif alert_type == "all":
				for f in ALERT_FIELDS: out["Alerts"][f] = setting

			elif alert_type == "none":
				for f in ALERT_FIELDS: out["Alerts"][f] = not setting
					
			# Decode Key-phrases		
			elif alert_type == "soon":
				out["Alerts"]["title"] = setting
				out["Alerts"]["game"] = setting
					
			elif alert_type == "bans":
				out["Alerts"]["ban"] = setting
				out["Alerts"]["unban"] = setting
					
			# Handle Everything Else
			else:
				out["Alerts"][alert_type] = setting



	# Helper Function For parse_preferences() Used to Expand Keywords
	# Pre-Condition: A Valid Settings Dictioary Has Been Provided in the Config File
	# Post-Condition: All Settings Fields in Dictionary Form Have Had Their Keywords Expanded
	def __parse_settings(out, settings):
		
		# Cycle through settings
		for item in settings:
			
			# Ignore alerts, there's a dedicated function for that
			if item == "Alerts":
				continue
			
			# If the user specifies message-specific settings, decode them
			if type(settings[item]) == dict:	
				out[item] = {}
				for key in settings[item]:

					# Parse Key-Phrases
					if key.lower() == "all":
						for k in {"live", "title", "game", "offline", "ban", "unban"}: out[item][k] = settings[item][key] # Forcing it to expand 'all' so other alert types can overwrite settings
					elif key.lower() == "bans":
						out[item]["ban"] = out[item]["unban"] = settings[item][key]
					elif key.lower() == "soon":
						out[item]["title"] = out[item]["game"] = settings[item][key]
					
					# Handle everything else
					elif key.lower() in {"live", "title", "game", "offline", "ban", "unban"}:
						out[item][key.lower()] = settings[item][key]
					
			# Handle general settings
			else:	
				out[item] = settings[item] # Note that we aren't validating datatypes in this function



	# A General Function For Parsing Settings From the Config File
	# The Function is Used by Both the Discord and Pushover Modules for Parsing Global and Streamer-Specific Settings
	# Pre-Condition: A Valid Settings Parameter Has Been Provided in the Config File
	# Post-Condition: A Dictionary of Settings Has Been Returned
	def parse_preferences(streamer, service):
		out = {}

		# If Service is Disabled, Disable All Notifications
		if service != "Logger" and service not in Config.enabled_modules:
			return out

		# Load All Settings for Service
		# We assume the config file has the "Streamers" key since the KeyError would have been caught in Streamer.init_all()
		if streamer == "GLOBAL" or (service + " Settings") in Config.config_file["Streamers"][streamer]:
			settings = Config.config_file[service + " Settings"] if streamer == "GLOBAL" else Config.config_file["Streamers"][streamer][service + " Settings"]
		else:
			return out

		# Add Everything But Alerts to Out
		Config.__parse_settings(out, settings)

		# Save Alert Settings, or Just Return
		if "Alerts" in settings:
			Config.__parse_alerts(out, settings["Alerts"], streamer=="GLOBAL")

		return out



	# Dumps the Contents of Config.config_file Back into the Original Config File
	# Pre-Condition: Config.config_file Contains the Updated Contents of config.json
	# Post-Condition: The COntents of Config.config_file Have Been Saved in config.json
	async def __save_config():

		# Try to dump the updated config_file into the config.json
		await Config.file_lock.acquire()
		try:
			file = open(Config.filename, "w")
			json.dump(Config.config_file, file, indent='\t', separators=(',',' : '))
			
			file.close()
			Config.file_lock.release()
		
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
		await Config.__save_config()



	# Used By TwitchAPI.__check_username() to Update Streamer Usernames that May Have Changed
	# Post-Condition: The Streamer's Entry in the Streamer Dictionary has Been Updated Without Changing the Order
	async def update_username(old_name, new_name):
		
		# Reload the config file before altering it
		await Config.load()

		# Copy the Streamers Into a New Dictionary and Replace the Username of Interest
		temp_dict = {}
		found = False
		for streamer in Config.config_file["Streamers"]:
			if not found and streamer == old_name:
				found = True
				temp_dict[new_name] = Config.config_file["Streamers"][old_name]
				continue
			
			temp_dict[streamer] = Config.config_file["Streamers"][streamer]
		
		# Replace Old Dictionary With New One
		Config.config_file["Streamers"] = temp_dict

		# Save the JSON
		await Config.__save_config()

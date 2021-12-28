from Exceptions import ConfigFormatError
from Notifications import Notifications
from Config import Config


# Special Classes for Indicating More Complex Datatypes
class dictOf():
	pass

class dictOfStr(dictOf):
	DATATYPE = str

class dictOfInt(dictOf):
	DATATYPE = int

class dictOfBool(dictOf):
	DATATYPE = bool



# *** DATATYPE CONSTANTS ***
# Primary Keys
REQUIRED_KEYS = {
	"Twitch Settings" : dict,
	"Logger Settings" : dict,
	"Streamers"       : dict
}
OPTIONAL_KEYS = {
	"Discord Settings"  : dict,
	"Pushover Settings" : dict
}

# Twitch Keys
TWITCH_REQUIRED_KEYS = {
	"Client ID"          : str,
	"Secret"             : str,
	"Reconnect Attempts" : int,
	"Reconnect Cooldown" : {float, int},
	"Refresh Rate"       : {float, int}
}

# Logger Keys
LOGGER_REQUIRED_KEYS = {
	"Log Level"    : str,
	"Log Filepath" : str
}
LOGGER_OPTIONAL_KEYS = {
	"Message Text" : {str, dictOfStr}
}
LOGGER_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}

# Pushover Keys
PUSHOVER_REQUIRED_KEYS = {
	"Soon Cooldown" : {float, int},
}
PUSHOVER_OPTIONAL_KEYS = {
	"Alerts"        : {str, dictOfBool},
	"API Token"     : {str, dictOfStr},
	"Group Key"     : {str, dictOfStr},
	"Embed URL"     : {str, dictOfStr},
	"Priority"      : {int, dictOfInt},
	"Devices"       : {str, dictOfStr},
	"URL Title"     : {str, dictOfStr},
	"Message Text"  : {str, dictOfStr},
	"Message Title" : {str, dictOfStr},
	"Sound"         : {str, dictOfStr}
}

# Discord Keys
DISCORD_REQUIRED_KEYS = {
	"Soon Cooldown" : {float, int}
}
DISCORD_OPTIONAL_KEYS = {
	"Alerts" :       {str, dictOfBool},
	"Bot Username" : {str, dictOfStr},
	"Avatar URL" :   {str, dictOfStr},
	"Webhook URL" :  {str, dictOfStr},
	"Message Text" : {str, dictOfStr},
	"Discord ID" :   {str, dictOfStr},
}

# Streamer Keys
STREAMER_REQUIRED_KEYS = {
	"Ban Status" : bool,
	"User ID" : str
}
STREAMER_OPTIONAL_KEYS = {
	"Discord Settings"  : dict, 
	"Pushover Settings" : dict
}

# Special Keys
ACCEPTABLE_ALERT_SPECIFIC_KEYWORDS = {"all", "soon", "bans", "live", "title", "game", "offline", "ban", "unban"}
ACCEPTABLE_ALERTS_KEYWORDS = {"all", "none", "soon", "bans", "live", "title", "game", "offline", "ban", "unban"}

# Alert Test Constants
ALERT_TYPES = {"live", "title", "game", "offline", "ban", "unban"}

LOGGER_REQUIRED_SETTINGS  = {"Message Text"}
PUSOVER_REQUIRED_SETTINGS = {"API Token", "Group Key", "Message Text"}
DISCORD_REQUIRED_SETTINGS = {"Webhook URL", "Message Text"}
REQUIRED_SETTINGS = {
	"Logger" : LOGGER_REQUIRED_KEYS,
	"Pushover" : PUSOVER_REQUIRED_SETTINGS,
	"Discord" : DISCORD_REQUIRED_SETTINGS
}



# General Function to Inspect the Keys of a Dictionary
# Post-Condition: If no errors/warnings have been raised...
# - The Dictionary Has All of the Required Keys
# - The Dictionary's Keys All Have the Correct Datatypes (if specified)
# - The Dictionary's Keys All Fall Under Either 'required_keys' or 'optional_keys'
def check_keys(warnings, parent, dictionary, required_keys={}, optional_keys={}):

	for key in required_keys:

		# Make sure the disctionary includes all of the required keys
		if key not in dictionary:
			raise ConfigFormatError("KeyError! Couldn't find key: \'" + key + "\' in " + parent)

		# Enforce datatypes if they are given
		if type(required_keys) == dict:
			check_datatypes(warnings, parent, key, dictionary, required_keys)
	
	for key in dictionary:

		# Check For Extra Keys
		if key not in required_keys and key not in optional_keys:
			warnings.add("Unrecognized key in \"" + parent + "\": " + key)

		# Enforce datatypes if they are given
		elif key in optional_keys:
			if type(optional_keys) == dict:
				check_datatypes(warnings, parent, key, dictionary, optional_keys)



# Helper Function for check_keys(). Checks the Datatype of a Specific Key Given that Key's Dictionary and a Dictionary of Datatypes
# Post-Condition: If no errors/warnings have been raised...
# - The Dictionary's Key is a Valid Datatype or Valid Special Key
# 	- Examples of Special Keys Include "Alerts" and Alert-Specific Settings
def check_datatypes(warnings, parent, key, target_dict, datatypes_dict):

	valid_type = False
	alert_specific = False

	target = target_dict[key]
	datatypes = datatypes_dict[key]

	# *** Validate Datatypes of Primary Keys ***
	# Case 1: 'datatypes' is a set of valid types
	if type(datatypes) == set:

		# Make Sure Target Type is in Set
		for dt in datatypes:
			if type(target) == dt or (type(target) == dict and dictOf.__subclasscheck__(dt)):
				valid_type = True
				alert_specific = type(target) == dict and dictOf.__subclasscheck__(dt)
	
	# Case 2: There's Only One Valid Datatype
	elif type(target) == datatypes or (type(target) == dict and dictOf.__subclasscheck__(datatypes)):
		valid_type = True
		alert_specific = type(target) == dict and dictOf.__subclasscheck__(datatypes)
	
	# *** Validate Datatypes Within Special eys ***
	if valid_type:
			# Check Alerts Formatting
			if key == "Alerts":
				check_alerts(warnings, parent + "/Alerts", target)

			# Check Keys With Alert-Specific Settings
			elif alert_specific:
				check_message_specific_settings(warnings, parent + "/" + key, target, ACCEPTABLE_ALERT_SPECIFIC_KEYWORDS, datatypes)
	else:
		raise ConfigFormatError("Data Type Error! Incorrect Datatype Given for \"" + key + "\" in \"" + parent + "\". Acceptable types: " + str(datatypes))



# Helper Function for check_datatypes(). Validates the Contents of the "Alerts" Key
def check_alerts(warnings, parent, alerts):

	# Check Alerts in String Form
	if type(alerts) == str:
		seperated_list = [x.strip().replace("!", "") for x in str(alerts).split(",")]
		for kw in seperated_list:
			if kw not in ACCEPTABLE_ALERTS_KEYWORDS:
				warnings.add("Unrecognized keyword in \"" + parent + "\": " + kw)

	# Check Alerts in Dictionary Form
	elif type(alerts) == dict:
		check_message_specific_settings(warnings, parent, alerts, ACCEPTABLE_ALERTS_KEYWORDS, {bool})



# Helper Function for check_datatypes(). Validates Alert-Specific Settings
def check_message_specific_settings(warnings, parent, dictionary, acceptable_keys, acceptable_datatypes):

	# Collect Accetpable Datatypes
	types = set()
	for dt in acceptable_datatypes:
		if dictOf.__subclasscheck__(dt):
			types.add(dt.DATATYPE)
		else:
			types.add(dt)

	for key in dictionary:
		# Check for unrecognized keys
		if key not in acceptable_keys:
			warnings.add("Unrecognized key in \"" + parent + "\": " + key)
		
		# Enforce Datatypes
		elif (type(types) == set and type(dictionary[key]) in types) or type(dictionary[key]) == types:
			continue
		else:
			raise ConfigFormatError("Data Type Error! Incorrect Datatype Given for \"" + key + "\" in \"" + parent + "\". Acceptable types: " + str(types))



# Runs Through Each Alert Type to Make Sure the Requisite Info is Present
def test_alerts(streamer, service):

	# Generate Parsed Global Settings
	parsed_global_settings = Config.parse_preferences("GLOBAL", service)

	# Generate Parsed Streamer Settings
	parsed_streamer_settings = Config.parse_preferences(streamer, service)

	for msg in ALERT_TYPES:
		
		# Check if Alerts Are Enabled for Type
		if service == "Logger" or Notifications.preference_resolver("Alerts", msg, parsed_global_settings, parsed_streamer_settings):
			
			# Make Sure All of the Required Message Fields Are Present
			missing_fields = set()
			for setting in REQUIRED_SETTINGS[service]:
				if Notifications.preference_resolver(setting, msg, parsed_global_settings, parsed_streamer_settings) == None:
					missing_fields.add(setting)
			
			if len(missing_fields) != 0:
				raise ConfigFormatError(service + " Alert Test Failed: Streamer \"" + streamer + "\" is missing required fields " + str(missing_fields) + " for alert type \"" + msg + "\"")



# Primary Function For Validator.py. Runs Through A Battery of Tests to Make sure the Config File is Valid
# Pre-Condition: Logger Has Been Initialized and Config File Has Been Loaded
def validate():

	warnings = set()

	# Check Overall Formatting
	if type(Config.config_file) == list:
		raise ConfigFormatError("config.json should look like a dictionary, not an array")

	# Check Primary Keys
	check_keys(warnings, "config.json", Config.config_file, REQUIRED_KEYS, OPTIONAL_KEYS)

	# Check Twitch Keys
	check_keys(warnings, "Twitch Settings", Config.config_file["Twitch Settings"], TWITCH_REQUIRED_KEYS)

	# Validate Refresh Rate
	if Config.config_file["Twitch Settings"]["Refresh Rate"] <= 0:
		raise ConfigFormatError("Refresh Rate Must Be Greter Than Zero")

	# Check Logger Keys
	check_keys(warnings, "Logger Settings", Config.config_file["Logger Settings"], LOGGER_REQUIRED_KEYS, LOGGER_OPTIONAL_KEYS)
	
	# Validate Log Level
	if str(Config.config_file["Logger Settings"]["Log Level"]).upper() not in LOGGER_LOG_LEVELS:
		("Unrecognized Log Level: \"" + str(Config.config_file["Logger Settings"]["Log Level"]) + "\". Defaulting to INFO.")

	# Check Pushover Keys
	if "Pushover Settings" in Config.config_file:
		Config.enabled_modules.add("Pushover")
		check_keys(warnings, "Pushover Settings", Config.config_file["Pushover Settings"], PUSHOVER_REQUIRED_KEYS, PUSHOVER_OPTIONAL_KEYS)

	# Check Discord Keys
	if "Discord Settings" in Config.config_file:
		Config.enabled_modules.add("Discord")
		check_keys(warnings, "Discord Settings", Config.config_file["Discord Settings"], DISCORD_REQUIRED_KEYS, DISCORD_OPTIONAL_KEYS)

	# Check Length of "Streamers" Array
	if not len(Config.config_file["Streamers"]):
		raise ConfigFormatError("\"Streamers\" Dictionary Cannot Be Empty")

	for streamer in Config.config_file["Streamers"]:
		
		# Check Main Keys in Streamer's Dictionary
		check_keys(warnings, "Streamers/" + streamer, Config.config_file["Streamers"][streamer], STREAMER_REQUIRED_KEYS, STREAMER_OPTIONAL_KEYS)

		# Check Keys Within Streamer's "Discord Settings"
		if "Discord Settings" in Config.config_file["Streamers"][streamer]:
			if "Discord" not in Config.enabled_modules:
				warnings.add("Discord Settings Given for " + streamer + " but no Global Discord settings were Found!")
			else:
				check_keys(warnings, "Streamers/" + streamer + "/Discord Settings", Config.config_file["Streamers"][streamer]["Discord Settings"], optional_keys=DISCORD_OPTIONAL_KEYS)
		
		# Check Keys Within Streamer's "Pushover Settings"
		if "Pushover Settings" in Config.config_file["Streamers"][streamer]:
			if "Pushover" not in Config.enabled_modules:
				warnings.add("Pushover Settings Given for " + streamer + " but no Global Pushover settings were Found!")
			else:
				check_keys(warnings, "Streamers/" + streamer + "/Pushover Settings", Config.config_file["Streamers"][streamer]["Pushover Settings"], optional_keys=PUSHOVER_OPTIONAL_KEYS)

		# Do A Dry-Run of Logger Alerts
		if str(Config.config_file["Logger Settings"]["Log Level"]).upper()in {"INFO", "DEBUG"}:
			try: test_alerts("GLOBAL", "Logger")
			
			except (KeyboardInterrupt, GeneratorExit): raise
			except:
				warnings.add("Missing or Incomplete \"Message Text\" Fields in \"Logger Settings\".\n\tChange Log Level or Provide Message Text for All Alert Types if You Don't Want to See This Message")

		# Do A Dry-Run of Discord/Pushover Alerts
		for service in Config.enabled_modules:
			test_alerts(streamer, service)
	
	return warnings

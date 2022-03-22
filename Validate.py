from Exceptions import ConfigFormatError


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

# Streamer Keys
STREAMER_REQUIRED_KEYS = {
	"Ban Status" : bool,
	"User ID" : str
}

# Special Keys
ACCEPTABLE_ALERT_SPECIFIC_KEYWORDS = {"all", "soon", "bans", "live", "title", "game", "offline", "ban", "unban"}
ACCEPTABLE_ALERTS_KEYWORDS = {"all", "none", "soon", "bans", "live", "title", "game", "offline", "ban", "unban"}
ALERT_TYPES = {"live", "title", "game", "offline", "ban", "unban"}
ALERT_DATATYPES = {str, (dict,bool)}



# Returns True if 'data' is a Dictionary of Streamer-Specific Settings
def is_alert_specific(data):
	
	# Verify Datatype
	if type(data) != dict:
		return False

	# Try to Find at Least One Alert-Specific Keyword
	data_keys = [k.lower() for k in data]
	for key in ACCEPTABLE_ALERT_SPECIFIC_KEYWORDS:
		if key in data_keys:
			return True
	else:
		return False



# General Function to Inspect the Keys of a Dictionary
# Post-Condition: If no errors/warnings have been raised...
# - The Dictionary Has All of the Required Keys
# - The Dictionary's Keys All Have the Correct Datatypes (if specified)
# - The Dictionary's Keys All Fall Under Either 'required_keys' or 'optional_keys'
def check_keys(dict_name, dictionary, required_keys={}, optional_keys={}):
	warnings = []

	# Make sure the disctionary includes all of the required keys
	for key in required_keys:
		if key not in dictionary:
			raise ConfigFormatError("KeyError! Couldn't find key: \'" + key + "\' in " + dict_name)

	# Collect Valid Datatypes (if any)
	datatypes = dict()
	if type(required_keys) == dict:
		datatypes.update(required_keys)
	if type(optional_keys) == dict:
		datatypes.update(optional_keys)

	for key in dictionary:

		# Check For Extra Keys
		if key not in required_keys and key not in optional_keys:
			warnings.append("Unrecognized key in \"" + dict_name + "\": " + key)

		# Check Alerts
		elif key == "Alerts":
			check_alerts(warnings, dict_name + "/Alerts", dictionary[key])

		# Enforce datatypes if they are given
		elif len(datatypes):
			if not check_types(dictionary[key], datatypes[key]):
				raise ConfigFormatError("Data Type Error! Incorrect Datatype Given for \"" + key + "\" in \"" + dict_name + "\". Acceptable types: " + type_string(datatypes[key]))

	return warnings



# Helper Function for check_keys(). Validates the Datatypes of a Target Dictionary's Keys Given Some Accepted Datatypes
# Post-Condition: Returns True if All of the Keys are Valid, False Otherwise
def check_types(target, acceptable_types):

	if type(acceptable_types) != set:
		acceptable_types = {acceptable_types}

	for dt in acceptable_types:
		if type(dt) == tuple:
			if check_nested_types(target, dt):
				return True

		elif type(dt) == type and type(target) == dt:
			return True
	
	else:
		return False



# Recursive Helper for check_types(). Parses Datatypes Given in Tuple Form
# Each Entry is A 'Layer,' so (dict, list, str) is a Dictionary of Lists of Strings
def check_nested_types(target, type_tuple, tuple_index=0):

	# Stop Recursing Once there Are No More Layers
	if tuple_index >= len(type_tuple):
		return True
	
	# Check the Target at the Current Recursion Level
	if not check_types(target, type_tuple[tuple_index]):
		return False

	# Check the Target's Items (if any)
	if type(target) in {dict, list}:
		for sub_target in target:
			if type(target) == dict: sub_target = target[sub_target]

			if not check_nested_types(sub_target, type_tuple, tuple_index+1):
				return False
	
	return True



# Helper Function for check_keys(). Validates the Contents of the "Alerts" Key
def check_alerts(warnings, dict_name, alerts):
	keys = []

	# Parse Alerts in String Form
	if type(alerts) == str:
		keys = [x.strip().replace("!", "") for x in str(alerts).split(",")]

	# Parse Alerts in Dictionary Form
	elif type(alerts) == dict:
		keys = alerts.keys()
	else:
		raise ConfigFormatError("Data Type Error! Incorrect Datatype Given for \"Alerts\" in \"" + dict_name + "\". Acceptable types: " + type_string(ALERT_DATATYPES))

	# Check for Extra Keys
	for kw in keys:
		if kw not in ACCEPTABLE_ALERTS_KEYWORDS:
			warnings.append("Unrecognized keyword in \"" + dict_name + "\": " + kw)



# Helper for check_keys(), Returns a Human-Readable String of Accepted Datatypes
def type_string(types):
	out = []

	for dt in types:
		if type(dt) == tuple:
			out.append(" of ".join([t.__name__ for t in dt]))
		else:
			out.append(dt.__name__)
	
	return ", ".join(out)



# Primary Function For Validator.py. Runs Through A Battery of Tests to Make sure the Config File is Valid
# Pre-Condition: Logger Has Been Initialized and Config File Has Been Loaded
def validate():
	from Config import Config

	# Check Overall Formatting
	if type(Config.config_file) == list:
		raise ConfigFormatError("config.json should look like a dictionary, not an array")

	# Check Primary Keys
	setting_keys = dict([(module.SETTINGS_KEY, dict) for module in Config.enabled_modules if hasattr(module, "SETTINGS_KEY")])
	warnings = check_keys("config.json", Config.config_file, REQUIRED_KEYS, setting_keys)

	# Check Twitch Keys
	warnings += check_keys("Twitch Settings", Config.config_file["Twitch Settings"], TWITCH_REQUIRED_KEYS)

	# Validate Refresh Rate
	if Config.config_file["Twitch Settings"]["Refresh Rate"] <= 0:
		raise ConfigFormatError("Refresh Rate Must Be Greter Than Zero")

	# Check Length of "Streamers" Array
	if not len(Config.config_file["Streamers"]):
		raise ConfigFormatError("\"Streamers\" Dictionary Cannot Be Empty")

	# Check Main Keys in Streamer's Dictionary
	for streamer in Config.config_file["Streamers"]:
		warnings += check_keys("Streamers/" + streamer, Config.config_file["Streamers"][streamer], STREAMER_REQUIRED_KEYS, setting_keys)
	
	return warnings

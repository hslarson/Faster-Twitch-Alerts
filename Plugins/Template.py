import asyncio # Any of the functions below can be defined as async functions as well

# Add this module to the list of known modules in Main.py
class myPlugin():

	# Where are you storing your plugin's settings in the config file?
	SETTINGS_KEY = "MY PLUGIN SETTINGS"

	# Make sure the plugin's settings were specified correctly in config file
	# You can optinally return a list of warning strings to display in the log file
	def validate():
		pass

	# Initialize the Module
	# Read Streamer.py to see what comes in the streamer dict.
	def init(streamer_dict: dict): 
		pass
	
	# Called every time an alert is triggered
	def alert(streamer_obj: dict, alert_type: str):
		pass

	# Plugin Destructor
	# Called immediately before the program exits
	# Errors here will be ignored
	def terminate():
		pass
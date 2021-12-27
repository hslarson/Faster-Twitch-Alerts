from Notifications import Notifications
from TwitchAPI import TwitchAPI
from Streamer import Streamer
from Validate import validate
from Config import Config
from Logger import Log

import traceback
import asyncio
import time


streamer_dict = {}
refresh_rate = 1
initialized = asyncio.Event()



# Runs Once to Initialize Modules and Builds Streamer Dict.
# Pre-Condition: Modules Have Been Included and Global Variables Have Been Declared
# Post-Condition: All Modules Have Been Initialized and the Stremer Dictionary has Been Populated
async def init():
	global streamer_dict
	global refresh_rate
	global initialized

	# Don't Initialize Multiple Times
	if initialized.is_set():
		return

	# Load and Validate The Config File
	await Config.load()
	validation_warnings = validate()

	# Fetch Refresh Rate
	refresh_rate = float(Config.config_file["Twitch Settings"]["Refresh Rate"])

	# Initialize Modules
	Log.init(Config.config_file)
	await TwitchAPI.init(Config.config_file)
	Notifications.init(Config.config_file)

	# Display Any Warnings that Arose During the Config Validation Process
	# We Had to Wait for Logs to Initialize Before Showing These
	for warning in validation_warnings:
		Log.logger.warning(warning)

	# Initialize the Dictionary of Streamers
	streamer_dict = await Streamer.init_all(Config.config_file)

	# Initialize Add-Ons
	if "Pushover" in Config.enabled_modules:
		from Plugins.Pushover import Pushover
		Pushover.init(streamer_dict)
			
	if "Discord" in Config.enabled_modules:
		from Plugins.Discord import Discord
		Discord.init(streamer_dict)

	# Set 'Initialized' Event
	initialized.set()
	Log.logger.info("Initialized Successfully. Awaiting Activity...")



# Loop to Pull Data and Send Alerts
# Pre-condition: init() has Executed Successfully
# Post-Condition: Loop has Terminated Due to an Error/Interrupt
async def poll():
	global streamer_dict

	while True:
		# Start a Timer
		start = time.time()

		# Get New Info on Streamers
		await Streamer.refresh_all(streamer_dict)

		# Handle Any Notifications that Arise
		await Notifications.send_all(streamer_dict, Log.logger)

		# Try to Maintain a Constant Refresh Rate
		time_remaining = (start + 1.0 / refresh_rate) - time.time()
		await asyncio.sleep( (time_remaining if time_remaining > 0 else 0) )



# Primary Error Handler
# Pre-Condition: An Error Has Been Caught in main()
# Post-Condition: Errors Have Been Recorded by Log Module or Recursion Limit Was Hit
async def error_handler(exception, kill_event):

	# Call Recursive Function
	fatal = await error_helper(exception, 0)

	# Perform Shutdown Operations
	if fatal or not initialized.is_set():
		kill_event.set()
		await shutdown()



# Recursive Helper for Error Handler
# Returns True for Fatal Errors
async def error_helper(exception, recursion_count=0):

	# Terminate the Program if More than 5 Errors Occur
	if recursion_count >= 5:
		print("\nToo Many Errors Occured While Handling Error!")
		print("Displaying Errors (Earliest First):\n")
		print("-"*50)
		traceback.print_exception(type(exception), exception, exception.__traceback__)
		print("-"*50)

		return True

	# Try to Handle the Original Exception
	try: return await Log.fail(exception)
	
	# If Any Errors Occur During the Handling of that Exception, Handle Those As Well
	except BaseException as err:
		return await error_helper(err,  recursion_count + 1)



# Shut Down the Program
# Pre-Condition: A Fatal Error Has Been Handled in error_handler()
# Post-Condition: All Modules Have Been Shut Down and a Closing Log Message Has Been Sent
async def shutdown():

	# Kill ClientSession Objects
	if hasattr(TwitchAPI, 'requests'):
		await TwitchAPI.requests.close()

	if hasattr(Notifications, 'requests'):
		await Notifications.requests.close()

	# Send Closing Message
	Log.sessionEnded()



# Set Up Event Loop
# Post-Condition: The terminate Event Has Been Set in error_handler()
def main():
	loop = asyncio.get_event_loop()
	
	terminate = asyncio.Event()
	while not terminate.is_set():
		
		# Run Primary Methods
		try:
			loop.run_until_complete( init() )
			loop.run_until_complete( poll() )

		except BaseException as err:
			loop.run_until_complete( error_handler(err, terminate) )	

	loop.close()



# Start Event Loop
if __name__ == "__main__":
	main()
	
from Notifications import Notifications
from TwitchAPI import TwitchAPI
from Streamer import Streamer
from Validate import validate
from Config import Config
from Logger import Log

import traceback
import asyncio
import time

# >>> LOAD PLUGINS <<<
from Plugins.Pushover import Pushover
from Plugins.Discord import Discord
Config.enabled_modules = [Pushover, Discord] 


streamer_dict = {}
refresh_rate = 1
initialized = asyncio.Event()
terminate = asyncio.Event()



# Runs Once to Initialize Modules and Builds Streamer Dict.
# Pre-Condition: Modules Have Been Included and Global Variables Have Been Declared
# Post-Condition: All Modules Have Been Initialized and the Streamer Dictionary has Been Populated
async def init():
	global streamer_dict
	global refresh_rate

	# Load and Validate The Config File
	await Config.load()
	validation_warnings =  validate()
	validation_warnings += Log.validate()

	# >>> VALIDATE PLUGINS <<<
	for module in Config.enabled_modules:
		if hasattr(module, "validate"):
			ret = await to_async(module.validate)()
			if type(ret) == list: validation_warnings += ret

	# Fetch Refresh Rate
	refresh_rate = float(Config.config_file["Twitch Settings"]["Refresh Rate"])

	# Initialize Modules
	Log.init(Config.config_file)
	TwitchAPI.init(Config.config_file)
	Notifications.init(Config.config_file)

	# Display Any Warnings that Arose During the Config Validation Process
	# We Had to Wait for Logs to Initialize Before Showing These
	for warning in validation_warnings:
		Log.logger.warning(warning)

	# Initialize the Dictionary of Streamers
	streamer_dict = await Streamer.init_all(Config.config_file)

	# >>> INITIALIZE PLUGINS <<<
	for module in Config.enabled_modules:
		if hasattr(module, "init"):
			await to_async(module.init)(streamer_dict)

	# >>> SET PLUGIN ALERT CALLBACK <<<
	Notifications.alert_callbacks = [Log.alert]
	for module in Config.enabled_modules:
		if hasattr(module, "alert"):
			Notifications.alert_callbacks.append(to_async(module.alert))
	
	# Start the Notification Handler
	# Any Alerts that Arose During Initialization Will Now Be Sent
	Notifications.Handler.streamer_dict = streamer_dict
	Notifications.Handler.ready.set()
	
	# Set 'Initialized' Event
	initialized.set()
	Log.logger.info("Initialized Successfully. Awaiting Activity...")



# Loop to Pull Data and Send Alerts
# Pre-condition: init() has Executed Successfully
# Post-Condition: Loop has Terminated Due to an Error/Interrupt
async def poll():
	global streamer_dict

	# Continuously Update Streamer Data
	while True:

		# Start a Timer
		start = time.time()

		# Checks Errors that Arose While Sending Notifications
		Notifications.Handler.check_tasks()

		# Get New Info on Streamers
		await Streamer.refresh_all(streamer_dict)

		# Try to Maintain a Constant Refresh Rate
		time_remaining = (start + 1.0 / refresh_rate) - time.time()
		await asyncio.sleep( (time_remaining if time_remaining > 0 else 0) )



# Primary Error Handler
# Pre-Condition: An Error Has Been Caught in main()
# Post-Condition: Errors Have Been Recorded by Log Module or Recursion Limit Was Hit
def error_handler(loop, exception):

	# Call Recursive Function
	fatal = error_helper(loop, exception, 0)

	# Perform Shutdown Operations
	if fatal or not initialized.is_set():
		terminate.set()
		loop.run_until_complete(shutdown())



# Recursive Helper for Error Handler
# Returns True for Fatal Errors
def error_helper(loop, exception, recursion_count):

	# Terminate the Program if More than 5 Errors Occur
	if recursion_count >= 5:
		print("\nToo Many Errors Occurred While Handling Error!")
		print("Displaying Errors (Earliest First):\n")
		print("-"*50)
		traceback.print_exception(type(exception), exception, exception.__traceback__)
		print("-"*50)

		return True

	# Try to Handle the Original Exception
	try:
		return loop.run_until_complete(Log.fail(exception))

	# If Any Errors Occur During the Handling of that Exception, Handle Those As Well
	except BaseException as err:
		return error_helper(loop, err, recursion_count + 1)



# Shut Down the Program
# Pre-Condition: A Fatal Error Has Been Handled in error_handler()
# Post-Condition: All Modules Have Been Shut Down and a Closing Log Message Has Been Sent
async def shutdown():

	# Kill All Alert Tasks
	await Notifications.Handler.stop()

	# Kill ClientSession Objects
	if hasattr(TwitchAPI, 'requests'):
		await TwitchAPI.requests.close()

	if hasattr(Notifications, 'requests'):
		await Notifications.requests.close()

	# >>> KILL PLUGINS <<<
	for module in Config.enabled_modules:
		if hasattr(module, 'terminate'):
			try: await to_async(module.terminate)()
			except: pass

	# Send Closing Message
	Log.sessionEnded()



# Returns an Asychronous Version of 'function'
def to_async(function):

	# Already async
	if asyncio.iscoroutinefunction(function):
		return function

	# Not async
	async def async_func(*args, **kwargs):
		return function(*args, **kwargs)
	
	return async_func



# Set Up Event Loop
# Post-Condition: The terminate Event Has Been Set in error_handler()
def main():
	loop = asyncio.get_event_loop()

	while not terminate.is_set():
		try:
			if not initialized.is_set():
				Notifications.Handler.start(loop)
				loop.run_until_complete( init() )
				
			loop.run_until_complete( poll() )

		except BaseException as err:
			error_handler(loop, err)

	loop.close()



# Start Event Loop
if __name__ == "__main__":
	main()

from Validate import is_alert_specific
from Exceptions import *
import aiohttp
import asyncio
import time


# A Class for Constructing and Sending Notifications
class Notifications():

	alert_callbacks = [] # A List of Functions to Call When We Want to Send an Alert


	# Initialize the Module
	# Pre-Condition: The Config File Has Been Loaded and Validated
	def init(config):
		Notifications.LIVE_COOLDOWN = 15

		# Start requests session
		client_timeout = aiohttp.ClientTimeout(total=10)
		Notifications.requests = aiohttp.ClientSession(timeout=client_timeout)



	# General Function for Sending Pushover and Discord Alerts
	# Pre-Condition: A Message Payload Has Been Generated in the Pushover/Discord Modules
	# Post-Condition: The Message Has Been Sent or An Error Occurred
	async def send(coro):
		try: response = await coro
		
		except (KeyboardInterrupt, GeneratorExit):
			raise
		except BaseException as err:
			raise RequestsError(err)		

		if response.status // 100 != 2:
			raise BadResponseCodeError(response)



	# Parse Python Expressions Enclosed in Curly Braces
	# Post-Condition: The String Has Been Formatted or an Error Occurred
	def special_format(format_string, **replace_vars):

		# Define Some Extra Local Variables
		replace_vars['time'] = time.localtime()
		replace_vars['nl'] = "\n"
		replace_vars['tb'] = "\t"
		replace_vars['dq'] = "\""
		replace_vars["sq"] = "\'"

		out_string = str(format_string)

		start_index = 0
		while 1:
			
			# Search for open brackets
			open_index = format_string.find('{', start_index)
			if open_index == -1:
				break

			# Search for closed brackets
			close_index = format_string.find('}', open_index)
			if close_index == -1:
				raise Exception
			
			# Evaluate the contents of the brackets and replace the brackets w/ the new string
			eval_str = str(eval(format_string[open_index+1 : close_index], replace_vars))
			out_string = out_string.replace( format_string[open_index : close_index+1], eval_str)
			
			start_index = close_index

		return out_string



	# Determines a User's Preferences for A Given Field
	# Post-Condition: The Setting Specified by setting_key Has Been Returned
	def preference_resolver(setting_key, message_type, global_settings={}, streamer_settings={}):

		for settings in [streamer_settings, global_settings]:

			# Search for Key in Settings Dictionary
			if setting_key in settings:

				if not is_alert_specific(settings[setting_key]):
					return settings[setting_key]

				elif message_type in settings[setting_key]:
					return settings[setting_key][message_type]
		
		else: return None



	# A Helper Function for Handler.new_alert()
	# Post-Condition: Notifications Have Been Sent By Logger and All Enabled Modules
	async def send_helper(streamer, message):

		# Wait for the Handler to Finish Initializing
		await Notifications.Handler.ready.wait()

		# Send Module Notifications
		coros = []
		for func in Notifications.alert_callbacks:
			coros.append(func(Notifications.Handler.streamer_dict[streamer], message))

		if len(coros):
			await asyncio.gather(*coros, return_exceptions=False)



	# Creates asyncio Tasks for Incoming Alerts and Manages Exceptions & Cancellations Related to Those Tasks
	class Handler:

		all_tasks = []
		ready = asyncio.Event()

		main_loop = None
		streamer_dict = None


		# Initializes the Handler With the Info Needed to Make Alerts
		def start(loop):
			Notifications.Handler.main_loop = loop
			Notifications.Handler.main_loop.set_exception_handler(lambda l, c: None) # Suppress Errors



		# Cancels All Pending Tasks
		# Post-Condition: All Tasks Have Been Cancelled
		async def stop():

			# Call Cancel Functions
			for task in Notifications.Handler.all_tasks:
				if not task.done():
					task.cancel()

			# Wait for All the Tasks to Finish
			# No Exception Handling Since the Program is Exiting
			await asyncio.gather(*Notifications.Handler.all_tasks, return_exceptions=True)



		# Create a New Alert Task
		# Pre-Condition: An Alert Has Been Triggered in the Streamer Module
		# Post-Condition: A New Task Has Been Created and Appended to the all_tasks List
		def new_alert(username, message):

			# Construct Coroutine
			coro = Notifications.send_helper(username, message)

			# Create Task and Add it to List
			Notifications.Handler.all_tasks.append( Notifications.Handler.main_loop.create_task(coro) )



		# Cleans the 'all_tasks' List and Raises Exceptions if There are Any
		# Post-Condition: Functions that Finished Successfully Have Been Removed from the List and the Oldest Exception (if Any) Has Been Raised and Removed
		def check_tasks():
			first_err = None
			out = []

			for task in Notifications.Handler.all_tasks:
				
				# Save Pending Tasks
				if task.done():

					# Store the First Exception we Find
					# Save All Other Exceptions
					if task.exception():
						if first_err == None:
							first_err = task.exception()
						else:
							out.append(task)
				else:
					out.append(task)
			
			# Replace Old List With Cleaned List
			Notifications.Handler.all_tasks = out

			# Raise the First Error if THere Was One
			if first_err:
				raise first_err

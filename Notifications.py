from Config import Config
from Exceptions import *
import aiohttp
import asyncio
import time


class Notifications():


	# Initialize the Module
	# Pre-Condition: The Config File Has Been Loaded and Validated
	def init(config):

		# Load Settings
		Notifications.LIVE_COOLDOWN = 15
		Notifications.LOGGER_GLOBAL_SETTINGS = Config.parse_preferences("GLOBAL", "Logger")

		# Start requests session
		client_timeout = aiohttp.ClientTimeout(total=10)
		Notifications.requests = aiohttp.ClientSession(timeout=client_timeout)



	# General Function for Sending Pushover and Discord Alerts
	# Pre-Condition: A Message Payload Has Been Generated in the Pushover/Discord Modules
	# Post-Condition: The Message Has Been Sent or An Error Occurred
	async def send(url, type, payload):
		try:
			if type == Notifications.PUSHOVER:
				response = await Notifications.requests.post(url, params=payload, timeout=10)
			else:
				response = await Notifications.requests.post(url, json=payload,   timeout=10)
		
		except (KeyboardInterrupt, GeneratorExit):
			raise
		except BaseException as err:
			raise RequestsError(payload, err)		

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

		format_string = str(format_string)
		out_string = format_string

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

				if type(settings[setting_key]) != dict:
					return settings[setting_key]

				elif message_type in settings[setting_key]:
					return settings[setting_key][message_type]
		
		else: return None



	# A Helper Function for Handler.new_alert()
	# Post-Condition: Notifications Have Been Sent By Logger and All Enabled Modules
	async def send_helper(streamer_obj, message, logger, pushover_enabled, discord_enabled):
		
		# Send Log Notification
		log_msg = Notifications.preference_resolver("Message Text", message, Notifications.LOGGER_GLOBAL_SETTINGS)
		if log_msg != None:						
			logger.info( Notifications.special_format(
				str(log_msg),

				name = streamer_obj.name,
				title = streamer_obj.last_title,
				game = streamer_obj.last_game,
				message = message
			))

		# Send Pushover and Discord Notifications
		coros = []
		if pushover_enabled:
			coros.append(Notifications.pushover(streamer_obj, message))

		if discord_enabled:
			coros.append(Notifications.discord(streamer_obj, message))

		if len(coros):
			await asyncio.gather(*coros, return_exceptions=False)



	# Creates asyncio Tasks for Incoming Alerts and Manages Exceptions & Cancellations Related to Those Tasks
	class Handler:

		all_tasks = []


		# Initializes the Handler With the Info Needed to Make Alerts
		def start(loop, streamer_dict, logger):
			Notifications.Handler.main_loop = loop
			Notifications.Handler.streamer_dict = streamer_dict
			Notifications.Handler.logger = logger



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
			coro = Notifications.send_helper(
				Notifications.Handler.streamer_dict[username],
				message, 
				Notifications.Handler.logger, 
				"Pushover" in Config.enabled_modules, 
				"Discord"  in Config.enabled_modules
			)

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

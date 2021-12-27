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
	# Pre-Condition: A Message Payload Has Been Generated in the Pusover/Discord Modules
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
			raise BadResponseCodeError(payload, response)



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



	# Cycle Through the Notification Queue and Send All Messages
	# Post-Condition: All Notifications Have Been Sent and the Streamers' Notification Queues are Empty
	async def send_all(streamer_dict, logger):
		coros = []
		for streamer in streamer_dict:
			coros.append(Notifications.send_helper(streamer_dict, streamer, logger, "Pushover" in Config.enabled_modules, "Discord"  in Config.enabled_modules))	
		
		await asyncio.gather(*coros, return_exceptions=False)



	# A Recursive Helper for send_all()
	# Post-Condition: An Individual Streamer's Notification Queue Has Been Cleared
	async def send_helper(streamer_dict, streamer, logger, pushover_enabled, discord_enabled):
		
		# Send Notifications in Order
		while len(streamer_dict[streamer].notification_queue):
			message = streamer_dict[streamer].notification_queue[0]

			# Send Log Notification
			log_msg = Notifications.preference_resolver("Message Text", message, Notifications.LOGGER_GLOBAL_SETTINGS)
			if log_msg != None:						
				logger.info( Notifications.special_format(
					str(log_msg),

					name = streamer,
					title = streamer_dict[streamer].last_title,
					game = streamer_dict[streamer].last_game,
					message = message
				))

			# Send Pushover and Discord Notifications
			coros = []
			if pushover_enabled:
				coros.append(Notifications.pushover(streamer_dict[streamer], message))

			if discord_enabled:
				coros.append(Notifications.discord(streamer_dict[streamer], message))

			if len(coros):
				await asyncio.gather(*coros, return_exceptions=False)

			# Remove Message From Queue
			streamer_dict[streamer].notification_queue.pop(0)

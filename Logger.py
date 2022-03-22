from Validate import ALERT_TYPES, check_keys
from Notifications import Notifications
from TwitchAPI import TwitchAPI
from Config import Config
from Exceptions import *
import logging
import asyncio
import os

# A Class for Logging and Exception Handling
class Log():

	logger = None
	initialized = asyncio.Event()

	SETTINGS_KEY = "Logger Settings"
	LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "ALERT", "DEBUG", "NOTSET"}
	MESSAGE_TEXT = dict()


	# Makes Sure that the Plugin Settings Given in the Config File Are Valid
	# Pre-Condition: Config File Has Been Loaded
	# Post-Condition: An Error Was Triggered or Warnings (if any) Have Been Returned
	def validate():
		
		# Recoginzed Settings
		REQUIRED_KEYS = {
			"Log Level"    : str,
			"Log Filepath" : str
		}
		OPTIONAL_KEYS = {
			"Message Text" : {str, (dict,str)}
		}

		# Check Logger Keys
		warnings = check_keys(Log.SETTINGS_KEY, Config.config_file[Log.SETTINGS_KEY], REQUIRED_KEYS, OPTIONAL_KEYS)

		# Validate Log Level
		if str(Config.config_file[Log.SETTINGS_KEY]["Log Level"]).upper() not in Log.LOG_LEVELS:
			warnings.append("Unrecognized Log Level: \"" + str(Config.config_file[Log.SETTINGS_KEY]["Log Level"]) + "\". Defaulting to INFO.")

		# Test Alerts
		if Config.config_file[Log.SETTINGS_KEY]["Log Level"].upper() in {"ALERT", "DEBUG"}:
			
			global_settings = Config.parse_preferences("GLOBAL", Log)
			for msg in ALERT_TYPES:

				text = Notifications.preference_resolver("Message Text", msg, global_settings)
				if text == None:
					warnings.append("No Log Message Given for Alert Type: " + msg)
				else:
					Log.MESSAGE_TEXT[msg] = text

		return warnings



	# Sets Up the Log File and Error Handler
	# Pre-condition: Log Level Has Been Set in Config File
	# Post-condition: Logger Has Been Created and A Log File Has Been Generated in logs/
	def init(config=None):

		if Log.initialized.is_set():
			return
		
		try:
			# Try to Load the Config File
			if config == None:
				config = Config.config_file

			# Set Log File Path
			rel_path = str(config[Log.SETTINGS_KEY]["Log Filepath"]).replace("\\", os.sep).replace("/", os.sep)
			logs_file = os.path.normpath( os.path.join(os.getcwd(), rel_path) )

			# Format Log File
			temp_file = open(logs_file, 'a')
			temp_file.write("\n" + '-'*64 + "\n\n")
			temp_file.close()

			# Create Error Handler
			handler = logging.FileHandler(logs_file, 'a', 'utf-8')
			handler.setFormatter(logging.Formatter('%(asctime)s (%(levelname)s) --> %(message)s', datefmt='%m-%d-%y %H:%M:%S'))

			Log.logger = logging.getLogger("Log")
			Log.logger.addHandler(handler)

		# Handle Exceptions or Set All-Good Flag
		except (KeyboardInterrupt, GeneratorExit):
			raise
		except BaseException as err:
			raise LogInitError(err)
		else:
			Log.initialized.set()
		
		# Create Custom Log Level
		logging.ALERT = 15
		logging.addLevelName(logging.ALERT, "ALERT")
		def alert(self, message, *args, **kws):
			if self.isEnabledFor(logging.ALERT):
				self._log(logging.ALERT, message, args, **kws) 
		logging.Logger.alert = alert
		
		# Set Log Level (Defaults to INFO)
		Log.logger.setLevel(logging.INFO)

		if config != None:
			log_level = str(config[Log.SETTINGS_KEY]["Log Level"]).upper() 
			if log_level in Log.LOG_LEVELS:
				Log.logger.setLevel(eval("logging." + log_level))



	# Called By Notifications Module to Display Streamer Activity in Logs
	async def alert(streamer_obj, message):
		log_msg = Notifications.preference_resolver(message, None, Log.MESSAGE_TEXT)

		if log_msg != None:						
			Log.logger.alert( Notifications.special_format(
				str(log_msg),

				name = streamer_obj.name,
				title = streamer_obj.last_title,
				game = streamer_obj.last_game,
				message = message
			))



	# Attempts to Reconnect to the Network by Recycling the get_token() Function
	# Pre-condition: A Network-Related Exception has Been Triggered
	# Post-condition: The Network Condition Has Been Reestablished or an Error Was Raised
	async def __reconnect():
		try:
			await TwitchAPI.get_token()
		except BaseException as err:
			return await Log.fail(err)
		else:
			return False



	# Handles All Errors that Make it to Main.py
	# Pre-condition: An Error has Occurred in One of the Try/Except Blocks in Main.py
	# Post-Condition: The Error Has Been Handled and the Return Code Has Indicated if the Error is Fatal (true->program ends, false->program continues)
	async def fail(exception):


		# For Debugging
		print("\n\nGOT ERROR OF TYPE: " + str(type(exception)) + "\n\n")
		

		# If the Logs Weren't Initialized, We Need to Do So Before We Can Handle Exceptions
		if not Log.initialized.is_set() and type(exception) != LogInitError:
			Log.init(None)

		# ***Handle Specific Exceptions***

		# Keyboard Interrupts
		if type(exception) == KeyboardInterrupt or type(exception) == GeneratorExit:
			Log.logger.info("Interrupt Detected. Goodbye!")
			return True

		# Log Initialization Errors
		# We Have to Use print() Here Since Logs Could Not Be Generated
		elif type(exception) == LogInitError:
			print("Failed to Initialize Logs!\nError Details:\n" + exception.details)
			return True

		# Requests Errors
		elif type(exception) == RequestsError:
			Log.logger.debug("Failed to Make Request in Function " + exception.function + ".\nDetails:\n" + str(exception.details))

			return await Log.__reconnect()

		elif type(exception) == BadResponseCodeError:
			msg = "Got a Bad Response Code From Request in Function " + exception.function + ". Status Code: " + str(exception.status_code)
			try:
				msg += "\nRequest URL:\n" + str(exception.response.request_info.real_url)
				msg += "\nResponse:\n"    + str(await exception.response.text())
			except: pass

			Log.logger.warning(msg)
			
			# Kill Program if the Request Was Bad
			if exception.response.status // 100 == 4:

				# Handle Rate-Limit Errors
				if exception.response.status == 429:
					await asyncio.sleep(60)
					return False

				return True
			
			return await Log.__reconnect()

		# TwitchAPI Errors
		elif type(exception) ==  MalformedResponseError:
			msg = "Couldn't Read Response From TwitchAPI.get_response(). Status Code: " + str(exception.status_code)
			try:
				msg += "\nRequest URL:\n" + str(exception.response.request_info.real_url)
				msg += "\nResponse:\n"    + str(await exception.response.text())
			except: pass

			msg += "\nException Details:\n" + exception.details
			Log.logger.warning(msg)
			return False

		elif type(exception) == MaxReconnectAttempts:
			Log.logger.error("Max Reconnect Attempts Reached. Exiting...")
			return True

		# Config Errors
		elif type(exception) == ConfigFileError or type(exception) == ConfigFormatError:
			Log.logger.error("Problem With config.json:\n\n" + exception.details + "\n")
			return True

		# Catch-All
		else:
			Log.logger.exception("Unrecognized Exception:\n")
			return True



	# Sends Closing Message
	def sessionEnded():
		if Log.initialized.is_set():
			Log.logger.info("Session Ended")
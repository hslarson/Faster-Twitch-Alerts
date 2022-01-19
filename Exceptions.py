from aiohttp import ClientResponse
import traceback


# Base Class For Custom Exceptions
class Error(Exception):

	# Format Exception Info
	def exception_str(exception):
		return "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

	# Find the Function Where the Error Was Raised
	def get_function():
		temp = traceback.format_stack()[-3]

		start_index = temp.find("in ") + 3
		end_index   = temp.find("\n    ")
		return temp[start_index : end_index] + "()"



# *** Requests Errors ***
# General-Purpose Error for HTTP Requests
class RequestsError(Error):
	def __init__(self, exception):
		self.function = Error.get_function()
		self.details = Error.exception_str(exception)

# Error for non-200 Response Codes
class BadResponseCodeError(Error):
	def __init__(self, response):
		self.function = Error.get_function()
		self.response = response
		self.status_code = 0

		if type(self.response) == ClientResponse:
			self.status_code = self.response.status


# *** TwitchAPI Errors ***
# Error for Unreadable Response JSON's
class MalformedResponseError(Error):
	def __init__(self, response, exception):
		self.details = Error.exception_str(exception)
		self.response = response
		self.status_code = 0

		if type(self.response) == ClientResponse:
			self.status_code = self.response.status

# Kills Program Once Reconnect Attempts are Exhausted
class MaxReconnectAttempts(Error):
	pass


# *** Log Errors ***
# Called When Logger Fails to Properly Initialize (Usually Due to File Permissions)
class LogInitError(Error):
	def __init__(self, exception):
		self.details = Error.exception_str(exception)


# *** Config Errors ***
# General-Purpose Error for Config File Issues
class ConfigFileError(Error):
	def __init__(self, exception):
		self.details = Error.exception_str(exception)

# Error for Missing or Incorrect Config Fields
class ConfigFormatError(Error):
	def __init__(self, details):
		self.details = details
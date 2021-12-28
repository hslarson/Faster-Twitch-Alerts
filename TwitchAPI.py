from Config import Config
from Exceptions import *
import aiohttp
import asyncio
import time


class TwitchAPI():

	# Initialize Module
	# Pre-Condition: The Config File Has Been Loaded and Validated
	def init(config):

		# OAuth Token Variables
		TwitchAPI.reload_token = 0
		TwitchAPI.auth_dict = None
		
		# Load Constants
		TwitchAPI.CLIENT_ID = config["Twitch Settings"]["Client ID"]
		TwitchAPI.SECRET = config["Twitch Settings"]["Secret"]
		TwitchAPI.RECONNECT_ATTEMPTS = config["Twitch Settings"]["Reconnect Attempts"]
		TwitchAPI.RECONNECT_COOLDOWN = config["Twitch Settings"]["Reconnect Cooldown"]

		# Start requests session
		client_timeout = aiohttp.ClientTimeout(total=10)
		TwitchAPI.requests = aiohttp.ClientSession(timeout=client_timeout)



	# Generates A Dictionary of Lists With Strings of Request URL's to Feed to get_response()
	# Pre-Condition: The Streamer Dictionary Has Been Populated
	# Post-Condition: URL_STRINGS Dictionary Has Been Filled
	def url_string_gen(streamer_dict):

		channel_out = []
		stream_out = []
		
		# Determine How Many API Calls Need to Be Made
		# Twitch Limits Calls to 100 Users Each
		streamers = list(streamer_dict.keys())
		iterations = len(streamers) // 100 + (1 if len(streamers) % 100 > 0 else 0)

		i = 0
		while i < iterations:
			i += 1

			# Split The Array Into 100-User Segments
			subarray = streamers[ (i-1)*100 : i*100 ]

			# Generate the URL String
			channel_url = "https://api.twitch.tv/helix/channels?"
			stream_url  = "https://api.twitch.tv/helix/streams?"
			for broadcaster in subarray:
				channel_url += "&broadcaster_id=" + str(streamer_dict[broadcaster].id)
				stream_url  += "&user_id=" + str(streamer_dict[broadcaster].id)
			
			# Add the String of ID's to their respective Lists
			channel_out.append(channel_url.replace("&", "", 1))
			stream_out.append(stream_url.replace("&", "", 1))

			TwitchAPI.URL_STRINGS = {
				"Channel" : channel_out,
				"Stream" : stream_out
			}



	# Gets the OAuth token from Twitch and Allows the Program to Test the Internet Connection
	# Post-Condition: A Dictionary with the OAuth Information Has Been Created
	async def get_token(initializing=False):

		# A negative reconnect limit denotes infinite attempts
		no_reconnect_limit = TwitchAPI.RECONNECT_ATTEMPTS < 0 
		attempts = int(initializing) + TwitchAPI.RECONNECT_ATTEMPTS

		while attempts or no_reconnect_limit:
			try:
				# Wait for Cooldown to Expire
				if not initializing:
					await asyncio.sleep(TwitchAPI.RECONNECT_COOLDOWN)

				# Make Request
				request_body = ("https://id.twitch.tv/oauth2/token?" +
							    "client_id=" + TwitchAPI.CLIENT_ID + 
								"&client_secret=" + TwitchAPI.SECRET + 
								"&grant_type=client_credentials")
				token = await TwitchAPI.requests.post(request_body, headers=None)

				# Handle Bad Reponse Codes
				if token.status // 100 != 2:
					raise BadResponseCodeError(token)

				# Extract token and expiration time
				token_json = await token.json()
				oauth_token = token_json["access_token"]
				TwitchAPI.reload_token = time.time() + int(token_json["expires_in"]) - 3600

			# Handle Exceptions
			except (KeyboardInterrupt, GeneratorExit, BadResponseCodeError, KeyError):
				raise
			except:
				attempts -= int(not no_reconnect_limit)
			else:
				# Generate Credential Dict.
				TwitchAPI.auth_dict = {
					'Client-ID' : TwitchAPI.CLIENT_ID,
					'Authorization' : 'Bearer ' + oauth_token
				}
				break
		else:
			raise MaxReconnectAttempts



	# Calls the Twitch API for Up-To-Date Streamer Information
	# Pre-Condition: THe Streamer DIctionary Has Been Initialized
	# Post-Condition: Data Has Been Recieved, Validated, and Stored in Output Dictionaries
	async def get_response(streamer_dict):
		
		# Reload OAuth Token if Necessary
		if time.time() > TwitchAPI.reload_token:
			await TwitchAPI.get_token(True)

		# Generate Coroutines Array for Requests
		coros = []
		for req_type in ["Channel", "Stream"]:
			coros += [TwitchAPI.requests.get(url, headers=TwitchAPI.auth_dict) for url in TwitchAPI.URL_STRINGS[req_type]]

		# Call the Twitch API
		try:
			responses = await asyncio.gather(*coros, return_exceptions=False)
		except (KeyboardInterrupt, GeneratorExit):
			raise
		except BaseException as exception:
			raise RequestsError(exception)

		# Split the Response List and Check Individual Responses
		split_responses = [responses[:int(len(responses)/2)], responses[int(len(responses)/2):]]
		out = [{}, {}]

		coros = []
		for index, req_type in enumerate(["Channel", "Stream"]):
			coros += [TwitchAPI.__check_response(streamer_dict, out[index], response, req_type) for response in split_responses[index]]
		await asyncio.gather(*coros, return_exceptions=False)
		
		return out



	# Helper Function For get_response(). Validates an Individual Response and Adds Data to data_dict if Valid
	# Pre-Condition: get_response() Received Responses from Twitch
	# Post-Condition: Valid Data Has Been Added to data_dict or an Error Was Raised
	async def __check_response(streamer_dict, data_dict, response, resp_type):
		
		# Check Response Code
		if response.status // 100 != 2:
			raise BadResponseCodeError(response)

		try:
			# Iterate Over Response JSON
			resp_json = await response.json()
			for dictionary in resp_json["data"]:
							
				# Get Streamer's Display Name and ID
				name = dictionary["broadcaster_name" if resp_type == "Channel" else "user_name"]
				id   = dictionary["broadcaster_id"   if resp_type == "Channel" else "user_id"]
						
				# Update the Username if Necessary
				# If a streamer's display name has changed, update it
				if name not in streamer_dict:
								
					# Search the dict by user id
					for streamer in streamer_dict:
											
						# If the id's match, change the key name and Streamer.name
						# Also Update the Config File
						if streamer_dict[streamer].id == id:
							await Config.update_username(streamer, name)

							streamer_dict[name] = streamer_dict[streamer]
							del streamer_dict[streamer]
												
							streamer_dict[name].name = name
							break
				
				# Add the Streamer to the Output Dict.
				data_dict[name] = dict(dictionary)

		except (KeyboardInterrupt, GeneratorExit):
			raise
		except:
			raise MalformedResponseError(response)

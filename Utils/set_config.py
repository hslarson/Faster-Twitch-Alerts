import pyperclip
import requests
import json
import os


# Load config file
try:
	file = open('../config.json', 'r')
	config = json.load(file)
	file.close()
except:
	print("Couldn't Open Config File")
	exit()


#Load settings from config file
try:
	client_id = config["Twitch Settings"]["Client ID"]
	secret = config["Twitch Settings"]["Secret"]
	oauth_token = ""
except:
	print("Incorrect Config.json Format")
	exit()



def binary_response(true_input, false_input, prompt="", case_sensitive=False):
	while 1:
		user_input = input(prompt + " (" + true_input + "/" + false_input +"): ")
		if (not case_sensitive and user_input.lower() == true_input.lower()) or (case_sensitive and user_input == true_input):
			return True
		elif (not case_sensitive and user_input.lower() == false_input.lower()) or (case_sensitive and user_input == false_input):
			return False
		else:
			print("Please Input '" + true_input + "' or '" + false_input + "'.")


def menu(options):

	while 1:
		choice = input("Your Choice: ")

		if choice.isdigit() and int(choice) <= len(options) and int(choice) > 0:
			return int(choice) - 1

		else:
			print("Invalid Choice. Please Choose a Number 1-" + str(len(options)))



class Titles():

	titles = []

	def show():

		os.system('cls' if os.name == 'nt' else 'clear')
		
		for title in Titles.titles:
			for line in title:
				print(line)
			print()
			
			

	def add(title, menu_options=None, underline_char=None):
		
		out = []
		out.append(title)

		if underline_char:
			out.append(underline_char*len(title))

		if menu_options:
			for index, option in enumerate(menu_options):
				out.append(str(index+1) + ". " + str(option))

		Titles.titles.append( tuple(out) )
	
	def pop():

		Titles.titles.pop()
		




# Adds A Streamer To The Config File
def add_streamer(response_json):

	# Do Some Organization
	name = response_json['data'][0]['display_name']
	if name in config["Streamers"]:
		add = binary_response("y", "n", "Streamer Already in Config File. Readding Them Will Erase Any Custom Preferences. Continue? ")
		if not add:
			return False

	config["Streamers"][name] = {}
	config["Streamers"][name]["Ban Status"] = False
	config["Streamers"][name]["User ID"] = response_json['data'][0]['id']
	
	try:
		file = open("../config.json", "w")
		json.dump(config, file, indent='\t', separators=(',', ' : '))
		file.close()
	except:
		Titles.add("Problem With Config File")
		raise
	else:
		return True



def show_similar(username):
	# Call API
		response = requests.get("https://api.twitch.tv/helix/search/channels?query="+username+"&first=5", headers=credentials)

		# Check Status Code
		try:
			if response.status_code != requests.codes.ok:
				raise Exception
			response_json = response.json()
			
			suggestions = [user["display_name"] for user in response_json['data']]
			suggestions.append("None of These")
			Titles.add("I Didn't Find an Exact Match, Did You Mean _____ ?", menu_options = suggestions)
			Titles.add("\bKeep in Mind That I Can't Find Streamers That Are Currently Banned")
			Titles.show()

			choice = menu(suggestions)
			Titles.pop()
			Titles.pop()

			return suggestions[choice] if choice != len(suggestions) - 1 else None

		except:
			raise


def show_details(response_json):
	user_info = response_json['data'][0]

	menu_options = []
	menu_options.append("User ID: " + user_info['id'])
	if "offline_image_url" in user_info and len(user_info["offline_image_url"]): menu_options.append("Offline Image URL: " + user_info["offline_image_url"])
	if "profile_image_url" in user_info and len(user_info["profile_image_url"]): menu_options.append("Profile Image URL: " + user_info["profile_image_url"])
	menu_options.append("Quit")
	Titles.add("\nUse The Numbers Below To Copy Info To Clipboard", menu_options, ".")

	Titles.show()
	while 1:
		menu_choice = menu(menu_options)

		if menu_choice == len(menu_options) - 1:
			break
		else:
			pyperclip.copy(str(menu_options[menu_choice])[str(menu_options[menu_choice]).index(": ") + 1:])
			print("Copied!\n")

	Titles.pop()



# Retrieves OAuth Token
def get_token():
	global oauth_token

	# Make the request
	retries = 10
	while (1):
		try:
			token = requests.post("https://id.twitch.tv/oauth2/token?" + "client_id=" + client_id + "&client_secret=" + secret + "&grant_type=client_credentials")

			# Handle the request
			if token.status_code != requests.codes.ok:
				raise Exception

			token_json = token.json()
			oauth_token = token_json["access_token"]

		except KeyboardInterrupt:
			raise KeyboardInterrupt
		except:
			return False
		else:
			return True




Titles.add("Press 'ctrl+c' at any time to quit", underline_char="=")

# Call the get_token function
if not get_token():
	Titles.add("Falied to get token")
	raise Exception


credentials = {
	'Client-Id' : client_id,
	'Authorization' : 'Bearer ' + oauth_token
}





# Main Loop
running = True
while running:
	try:
		# Get user input
		Titles.show()
		username = input("Input Username: ")

		# Call API
		response = requests.get("https://api.twitch.tv/helix/users?login="+username, headers=credentials)

		# Check Status Code
		try:
			if response.status_code != requests.codes.ok:
				raise Exception

			response_json = response.json()
			
			# Search For Streamer
			found = False
			for streamer in response.json()["data"]:
				if streamer["login"] == username.lower():
					found = True	
			if not found:
				choice = show_similar(username)
				if choice:
					new_response = requests.get("https://api.twitch.tv/helix/users?login="+choice, headers=credentials)
					if response.status_code != requests.codes.ok:
						raise Exception
					response_json = new_response.json()
				else:
					continue


			# If a User is Found
			menu_options = ["Add To Config File","Show User Details", "Restart Search"]
			Titles.add("Found User: " + response_json["data"][0]["display_name"] +". Now What?", menu_options, "-")
			while 1:
				Titles.show()
				menu_choice = menu(menu_options)
				if menu_choice == 0:
					if add_streamer(response_json):
						Titles.add("Generated Channel Settings for " + response_json["data"][0]["display_name"])

				elif menu_choice == 1:
					show_details(response_json)
				else:
					break

			while len(Titles.titles) > 1:
				Titles.pop()
			
		
		except KeyboardInterrupt:
			raise	
		except:
			Titles.add("Somting went Wrong With My API Call. Exiting...")
			running = False
	
	# Handle interrupts
	except KeyboardInterrupt:
		Titles.add("Goodbye!")
		running = False

Titles.show()
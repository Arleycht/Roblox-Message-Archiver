import json
import requests
import sys
import time

from pathlib import Path
from selenium.webdriver.common.by import By
from selenium import webdriver


def download(url: str, cookies: dict={}):
	try:
		response = requests.get(url, cookies=cookies)
		
		if response.status_code == 200:
			return response
		else:
			print(f"Failed to retrieve webpage. Status code: {response.status_code}")
	except Exception as e:
		raise e


def main():
	screenshot_delay = 2
	page_delay = 2
	
	json_format_url = "https://privatemessages.roblox.com/v1/messages?messageTab={}&pageNumber={}&pageSize=20"
	page_format_url = "https://www.roblox.com/my/messages/#!/{}?page={}&messageIdx={}"
	
	# Create directories
	Path("output/").mkdir(exist_ok=True)
	Path("output/images").mkdir(exist_ok=True)
	Path("output/json").mkdir(exist_ok=True)
	Path("addons/").mkdir(exist_ok=True)
	
	# Read secret key
	with open("secret.txt", "r") as f:
		roblosecurity = f.read()
	
	requests_cookies = {".ROBLOSECURITY": roblosecurity}
	driver_cookie = {"name": ".ROBLOSECURITY", "value": roblosecurity, "domain": "roblox.com"}
	
	# Download ublock for faster loading of web pages
	if not Path("addons/ublock.xpi").exists():
		addon = download("https://addons.mozilla.org/firefox/downloads/file/4359936/ublock_origin-1.60.0.xpi").content
		
		with open("addons/ublock.xpi", "wb") as f:
			f.write(addon)
	
	# Start web driver
	driver = webdriver.Firefox()
	driver.maximize_window()
	
	# Install ublock
	driver.install_addon("addons/ublock.xpi")
	
	# Initialize website with cookies
	driver.get("https://www.roblox.com/")
	driver.add_cookie(driver_cookie)
	driver.get("https://www.roblox.com/my/messages/#!/inbox")
	
	for tab_name in ["inbox", "sent", "archive"]:
		print(f"Getting page count for {tab_name}")
		
		s = download(json_format_url.format(tab_name, 0), cookies=requests_cookies).text
		data = json.loads(s)
		pretty_s = json.dumps(data, indent=4, sort_keys=True)
		
		page_count = data["totalPages"]
		page_message_counts = []
		
		print(f"Getting JSON for {page_count} pages")
		
		# Download page JSON data
		for i in range(page_count):
			json_path = f"output/json/{tab_name}_page_{i}.json"
			
			if not Path(json_path).exists():
				if i != 0:
					s = download(json_format_url.format(tab_name, i), cookies=requests_cookies).text
					data = json.loads(s)
					pretty_s = json.dumps(data, indent=4, sort_keys=True)
				
				with open(json_path, "w") as f:
					f.write(pretty_s)
			else:
				with open(json_path, "r") as f:
					data = json.load(f)
			
			page_message_counts.append(len(data["collection"]))
		
		for page_index in range(page_count):
			is_first_message_of_page = True
			message_count = page_message_counts[page_index]
			
			for message_index in range(message_count):
				screenshot_path = f"output/images/{tab_name}_message_{page_index}_{message_index}.png"
				
				if not Path(screenshot_path).exists():
					print(f"Loading {tab_name} page {page_index + 1} message {message_index + 1}/{message_count}")
					
					driver.get(page_format_url.format(tab_name, page_index + 1, message_index))
					
					if is_first_message_of_page:
						time.sleep(page_delay)
						is_first_message_of_page = False
					
					time.sleep(screenshot_delay)
					
					# Remove chat container because it partially obscures a part
					# of the message display on large messages
					try:
						chat_element = driver.find_element(By.ID, "chat-container")
						driver.execute_script("arguments[0].parentNode.removeChild(arguments[0])", chat_element)
					except Exception as _:
						pass
					
					driver.save_full_page_screenshot(screenshot_path)
					
					print(f"Saved screenshot {screenshot_path}")
	
	driver.quit()
	
	print("Done!")


if __name__ == "__main__":
	main()

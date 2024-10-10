import argparse
import json
import requests
import time

from pathlib import Path
from selenium.webdriver.common.by import By
from selenium import webdriver


screenshot_delay = 2
page_delay = 2

json_format_url = "https://privatemessages.roblox.com/v1/messages?messageTab={}&pageNumber={}&pageSize=20"
page_format_url = "https://www.roblox.com/my/messages/#!/{}?page={}&messageIdx={}"


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
	parser = argparse.ArgumentParser()
	parser.add_argument("token_path", help="Path to a file containing a ROBLOSECURITY token")
	parser.add_argument("-o", "--output", "--output_dir", dest="output_dir", default="output/", help="Output directory for JSON and image data")
	
	args = parser.parse_args()
	
	if Path(args.token_path).exists():
		with open(args.token_path) as f:
			token = f.read()
	else:
		print("Could not find specified file path for ROBLOSECURITY token")
		return
	
	output_dir = Path(args.output_dir)
	image_dir = output_dir / "images"
	json_dir = output_dir / "json"
	addons_dir = Path("addons/")
	
	# Create directories
	output_dir.mkdir(exist_ok=True)
	image_dir.mkdir(exist_ok=True)
	json_dir.mkdir(exist_ok=True)
	addons_dir.mkdir(exist_ok=True)
	
	# Download ublock for faster loading of web pages
	ublock_dir = addons_dir / "ublock.xpi"
	if not Path(ublock_dir).exists():
		print("Downloading ublock for faster loading")
		
		addon = download("https://addons.mozilla.org/firefox/downloads/file/4359936/ublock_origin-1.60.0.xpi").content
		
		with open(ublock_dir, "wb") as f:
			f.write(addon)
	
	# Start web driver
	driver = webdriver.Firefox()
	driver.maximize_window()
	
	# Install ublock
	driver.install_addon(ublock_dir)
	
	# Initialize website with cookies
	driver.get("https://www.roblox.com/")
	driver.add_cookie({"name": ".ROBLOSECURITY", "value": token, "domain": "roblox.com"})
	driver.get("https://www.roblox.com/my/messages/#!/inbox")
	
	print("Waiting for initial page load")
	time.sleep(3)
	
	requests_cookies = {".ROBLOSECURITY": token}
	
	for tab_name in ["inbox", "sent", "archive"]:
		print(f"Getting page count for {tab_name}")
		
		s = download(json_format_url.format(tab_name, 0), cookies=requests_cookies).text
		data = json.loads(s)
		
		total_message_count = data["totalCollectionSize"]
		page_count = data["totalPages"]
		page_message_counts = []
		
		print(f"Found {total_message_count} messages")
		print(f"Getting JSON for {page_count} pages")
		
		# Download page JSON data
		for i in range(page_count):
			json_path = json_dir / f"{tab_name}_page_{i}.json"
			
			if Path(json_path).exists():
				with open(json_path, "r") as f:
					data = json.load(f)
			else:
				s = download(json_format_url.format(tab_name, i), cookies=requests_cookies).text
				data = json.loads(s)
				pretty_s = json.dumps(data, indent=4, sort_keys=True)
				
				with open(json_path, "w") as f:
					f.write(pretty_s)
			
			page_message_counts.append(len(data["collection"]))
		
		for page_index in range(page_count):
			is_first_message = True
			message_count = page_message_counts[page_index]
			
			for message_index in range(message_count):
				screenshot_path = image_dir / f"{tab_name}_message_{page_index}_{message_index}.png"
				
				if screenshot_path.exists():
					continue
				
				print(f"Loading {tab_name} page {page_index + 1}/{page_count} message {message_index + 1}/{message_count}")
				
				driver.get(page_format_url.format(tab_name, page_index + 1, message_index))
				
				if is_first_message:
					is_first_message = False
					time.sleep(page_delay)
				
				time.sleep(screenshot_delay)
				
				# Remove chat container because it partially obscures a part
				# of the message display on large messages
				try:
					chat_element = driver.find_element(By.ID, "chat-container")
					driver.execute_script("arguments[0].parentNode.removeChild(arguments[0])", chat_element)
				except Exception as _:
					pass
				
				driver.save_full_page_screenshot(str(screenshot_path))
				
				print(f"Saved screenshot {screenshot_path}")
	
	driver.quit()
	
	print("Done!")
	print("It is recommended to delete the token file once you're done to avoid accidentally leaking it!")


if __name__ == "__main__":
	main()

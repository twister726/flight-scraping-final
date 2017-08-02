from pyvirtualdisplay import Display
import time
import threading
from queue import Queue
from dateutil.parser import parse
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Create the virtual display for running on a server
display = Display(visible=0, size=(1920, 1080))
display.start()

# Log initial time
print('Time at start of script:')
print(time.strftime('%d/%m/%y,%H:%M:%S'))

# Load list of airport codes from a file
airport_codes = []
with open('airports.txt') as f:
	airport_codes = [i.replace('\n', '') for i in f.readlines()]

# Check if a row of a flight table of an aircraft is of a domestic or international flight
def is_domestic(row, plane_code):
	try:
		# To set the position of required table cells in the web page
		OFFSET = 1
		# For Chrome
		tds = row.select('td')
		# INDEX WARNING
		from_code = tds[2 + OFFSET].find('a').text.replace('(', '').replace(')', '').strip()
		to_code = tds[3 + OFFSET].find('a').text.replace('(', '').replace(')', '').strip()
		if (from_code not in airport_codes) or (to_code not in airport_codes):
			return False
		return True
	# In case of incomplete rows
	except AttributeError as e:
		print(e)
		print('AttributeError in Plane ' + plane_code)
		return False

# Take the content of the table row in the flight table and return a neat string of data which will be written in the output file
def store_row(row_data, plane_details):
	# print('row_data', row_data)
	new_data = row_data[:]

	# Only on server
	new_data.pop(0)

	# Flight date
	dt = parse(new_data[1])
	new_data[1] = dt.strftime('%d/%m/%Y')

	# Airport codes
	for i in [2, 3]:
		# For Chrome
		new_data[i] = new_data[i][new_data[i].index("(") + 1:new_data[i].rindex(")")]
		# For PhantomJS
		# new_data[i] = new_data[i].split()[1]

	# Flight number
	new_data[4] = new_data[4].split()[0]

	# Flight times
	for i in [6, 7, 8]:
		# For Chrome
		temp = new_data[i].split()
		new_data[i] = temp[0] + ' ' + temp[1]
		# For PhantomJS
		pass

	# Final time
	temp = new_data[10].split()
	# For Chrome
	new_data[10] = temp[1] + ' ' + temp[2]
	# For PhantomJS
	# new_data[10] = temp[1]

	# Delete useless elements
	useless_indices = [0, 9, 11, 12]
	for i in reversed(useless_indices):
		new_data.pop(i)

	return ','.join(new_data + plane_details) + '\n'

# Save the most recent flight of the plane_code if it's domestic
def save_most_recent_flight(plane_code, browser):
	# For Chrome
	# STATUS_TD_INDEX = 11
	# For PhantomJS
	STATUS_TD_INDEX = 11

	plane_code = plane_code.lower()

	browser.get('https://www.flightradar24.com/data/aircraft/' + plane_code)
	# Wait for tbl-datatable not not contain 'Loading'
	time.sleep(2)

	# Try reloading the page until it either succeeds or fails num_tries times
	num_tries = 3
	for _ in range(num_tries - 1):
		try:
			WebDriverWait(browser, 8).until_not(
				EC.text_to_be_present_in_element((By.ID, 'tbl-datatable'), 'Loading')
			)
		except Exception:
			browser.get('https://www.flightradar24.com/data/aircraft/' + plane_code)
			time.sleep(2)
		else:
			break
	WebDriverWait(browser, 8).until_not(
		EC.text_to_be_present_in_element((By.ID, 'tbl-datatable'), 'Loading')
	)

	soup = bs(browser.page_source, 'lxml')

	# Get the plane-level details from the page
	plane_fields = [label.text.strip() for label in soup.select('#cnt-aircraft-info label')]
	plane_details = [span.text.strip() for span in soup.select('#cnt-aircraft-info .details')]
	plane_fields[-1] = 'AGE'
	plane_fields.insert(0, 'CODE')
	plane_details.insert(0, plane_code.upper())

	table_rows = soup.select('#tbl-datatable tbody tr')
	recent_index = 0
	for recent_index in range(len(table_rows)):
		row = table_rows[recent_index]
		tds = row.select('td')
		status_td = tds[STATUS_TD_INDEX]
		if 'Landed' in status_td.text:
			break
	recent_row = table_rows[recent_index]
	# print('recent_index', recent_index)
	# print('recent_row', recent_row)

	if is_domestic(recent_row, plane_code) and recent_index != len(table_rows) - 1:
		# For Chrome
		# recent_data = [td.text.strip() for td in recent_row.select('td.hidden-xs.hidden-sm')]
		# For PhantomJS
		recent_data = [td.text.strip() for td in recent_row.select('td')]
		return store_row(recent_data, plane_details)
	else:
		print('Last landed flight not domestic for plane ' + plane_code)
		return ''

# Get all the currently active and inactive plane codes of the required airlines
def get_all_planes():
	print('Starting get_all_planes...')
	# airline_urls = ['https://www.flightradar24.com/data/aircraft/air-india-ai-aic']
	airline_urls = []
	with open('airlines.txt') as f:
		airline_urls = [i.replace('\n', '') for i in f.readlines()]

	all_active_planes = []
	all_inactive_planes = []

	def worker(url):
		browser = webdriver.Chrome()
		# browser = webdriver.PhantomJS()
		browser.get(url)
		time.sleep(3)
		soup = bs(browser.page_source, 'lxml')

		all_planes = [a.text.strip() for a in soup.select('.parent ul li a')]
		active_planes = [a.text.strip() for a in soup.select('.parent ul li .fbold')]
		inactive_planes = [p for p in all_planes if p not in active_planes]

		all_active_planes.extend(active_planes)
		all_inactive_planes.extend(inactive_planes)

		browser.close()
		print('Finished one worker')

	threads = []
	for url in airline_urls:
		t = threading.Thread(target=worker, args=(url,))
		threads.append(t)
		t.start()
		# For sequential scraping of airlines
		t.join()

	print('Finished get_all_planes')
	print(str(len(all_active_planes)) + ' active planes')
	print(str(len(all_inactive_planes)) + ' inactive planes')
	return all_active_planes, all_inactive_planes

# The number of threads to scrape parallelly in
num_threads = 2
download_queue = Queue()
save_queue = Queue()

# Thread worker function that pulls planes whose flights to scrape from a queue
def save_thread(q):
	browser = webdriver.PhantomJS()
	while True:
		plane_code = q.get()
		print('Trying plane ' + plane_code)
		try:
			result = save_most_recent_flight(plane_code, browser)
			print(plane_code + ' >> ' + result)
			if result:
				save_queue.put(result)
		except Exception as e:
			print ('Error in plane ' + plane_code)
			print(type(e))
			print(e)
			continue
		q.task_done()

# Worker function for the thread that periodically saves output from another queue.
def store_in_file(q):
	sleep_interval = 10 * 60
	num_to_save = 100

	while True:
		time.sleep(sleep_interval)
		num_saved = 0
		lines = []

		# Get at most num_to_save items from the queue
		while (not q.empty()) and (num_saved <= num_to_save):
			line = q.get()
			lines.append(line)
			num_saved += 1

		filename = time.strftime('%d-%m-%y,%H:%M:%S') + '.csv'
		with open('output/' + filename, 'a+') as f:
			for line in lines:
				f.write(line)
		print('Wrote file ' + filename)

# Initialize and start the scraping worker threads
threads = []
for i in range(num_threads):
	t = threading.Thread(target=save_thread, args=(download_queue,))
	t.setDaemon(True)
	t.start()

# Start the thread that saves scraped data to files
store_thread = threading.Thread(target=store_in_file, args=(save_queue,))
store_thread.setDaemon(True)
store_thread.start()

first_run_flag = True # If running for the first time, set planes to check to all inactive planes
planes_to_save = []

while True:
	active_planes, inactive_planes = get_all_planes()
	if first_run_flag:
		planes_to_save += inactive_planes
		first_run_flag = False

	for plane_code in inactive_planes:
		if plane_code in planes_to_save:
			print('Queueing plane ' + plane_code)
			download_queue.put(plane_code)
			# Remove all occurrences of plane_code from planes_to_save
			planes_to_save[:] = [i for i in planes_to_save if i != plane_code]

	# Add active planes which were not there before
	planes_to_save += [i for i in active_planes if i not in planes_to_save]

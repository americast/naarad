from __future__ import print_function

import re
import json
from dateutil.parser import parse, tz
import urllib.request
import os
from random import random
import time
from datetime import datetime, timezone
import pytz

import facepy
from facepy import GraphAPI

from frontend import write_html

# Put Facebook 'Access Token' in a plain text file ACCESS_TOKEN in same dir.
# To get an access token follow this SO answer:
# http://stackoverflow.com/a/16054555/1780891

# with open('./ACCESS_TOKEN', 'r') as f:
# 	access_token = f.readline().rstrip('\n')

access_token=str(os.environ['ACCESS_TOKEN'])
graph = GraphAPI(access_token)


def get_comments(post_id):
	base_query = post_id + '/comments'

	# scrape the first page
	print('scraping:', base_query)
	comments = graph.get(base_query)
	data = comments['data']
	return data


def get_picture(post_id, dir="."):
	base_query = post_id + '?fields=object_id'
	try:
		pic_id = graph.get(base_query)['object_id']
	except KeyError:
		return None

	try:
		pic = graph.get('{}?fields=images'.format(pic_id))
		return (pic['images'][0]['source'])
		# f_name = "{}/{}.png".format(dir, pic_id)
		# f_handle = open(f_name, "wb")
		# f_handle.write(pic)
		# f_handle.close()
		# return "{}.png".format(pic_id)
	except facepy.FacebookError:
		return None


def get_event_picture(post_id, dir="."):
	base_query = post_id + '?fields=object_id'
	try:
		pic_id = graph.get(base_query)['object_id']
	except KeyError:
		return None
	try:
		pic = graph.get('{}?fields=cover'.format(pic_id))
		return (pic['cover']['source'])
		# urllib.request.urlretrieve(pic['cover']['source'] , "{}/{}.png".format(dir, pic_id))
		# return "{}.png".format(pic_id)
	except facepy.FacebookError:
		return None


def get_link(post_id):
	base_query = post_id + '?fields=link'

	try:
		link = graph.get(base_query)['link']
	except KeyError:
		return None

	return link


def get_event(post_id, page_id):
	base_query = page_id + '/events'
	all_events = graph.get(base_query)

	message = """
{}
Date: {}
Time: {}
Veunu: {}
	"""
	for event in all_events['data']:
		if event['id'] in post_id:
			DateTime = prettify_date([{'created_time': event['start_time']}])
			try:
				if 'description' in event.keys():  # checking if the event have description
					message = message.format(event['description'],
											 DateTime[0]['real_time'],
											 DateTime[0]['real_date'],
											 event['place']['name'])
				else:
					message = message.format(event['name'],
											 DateTime[0]['real_time'],
											 DateTime[0]['real_date'],
											 event['place']['name'])
			except: pass
			return message


def get_shared_post(post_id):
	print (post_id)
	base_query = post_id + '?fields=parent_id'
	# getting id of the original post
	try :	
		parent_id = graph.get(base_query)['parent_id']
		query = parent_id + '?fields=message'
	except KeyError :
		query = post_id + '?fields=message'
	try :
		original_message = graph.get(query)['message']
	except KeyError :
		original_message = ""
	return original_message

def get_video(post_id) :
	video_id = post_id.split('_')[1]
	base_url = video_id + "?fields=embeddable"
	try : 
		embed_flag = graph.get(base_url)['embeddable'] 
	except facepy.exceptions.OAuthError:
		return ""
	if embed_flag : #checking if the video is embedddable 
		embed_html_url=video_id + '?fields=from,source'
		query = graph.get(embed_html_url)
		video_url = query['source']
		page_name = query['from']['name']
		msg = """<b>{} shared the following video\n\n
				<video width="320" height="240" controls>
				<source src="{}" >
				 Your browser does not support the video tag.
					</video>""".format(page_name,video_url)
		return msg
	else : 
		return ""
def get_feed(page_id, pages=10):
	# check last update time
	try:
		old_data = json.load(open('docs/{}.json'.format(page_id), 'r'))
		last_post_time = parse(old_data[0]['created_time'])
	except FileNotFoundError:
		old_data = []
		last_post_time = parse("1950-01-01T12:05:06+0000")

	base_query = page_id + '/feed?limit=2'

	# scrape the first page
	print('scraping:', base_query)
	feed = graph.get(base_query)
	new_page_data = feed['data']

	data = []
	is_new_post = (parse(new_page_data[0]['created_time']) > last_post_time)

	if is_new_post:
		data = new_page_data

	# determine the next page
	next_page = feed['paging']['next']
	next_search = re.search('.*(\&until=[0-9]+)', next_page, re.IGNORECASE)
	if next_search:
		the_until_arg = next_search.group(1)

	pages = pages - 1

	# scrape the rest of the pages
	while (next_page is not False) and is_new_post and pages > 0:
		the_query = base_query + the_until_arg
		print('baking:', the_query)
		try:
			feed = graph.get(the_query)
			new_page_data = feed['data']
			is_new_post = (
				parse(new_page_data[0]['created_time']) > last_post_time)

			data.extend(new_page_data)
		except facepy.exceptions.OAuthError:
			print('start again at', the_query)
			break

		# determine the next page, until there isn't one
		try:
			next_page = feed['paging']['next']
			next_search = re.search(
				'.*(\&until=[0-9]+)', next_page, re.IGNORECASE)
			if next_search:
				the_until_arg = next_search.group(1)
		except IndexError:
			print('last page...')
			next_page = False
		pages = pages - 1
		for post_dict in data:
			post_dict['pic'] = get_picture(post_dict['id'], dir='docs')
			post_dict['link'] = get_link(post_dict['id'])
			if "story" in post_dict :  #Events and shared post have story key
				if "event" in post_dict['story'] :
					post_dict['message'] = get_event(post_dict['id'], page_id)
					post_dict['pic'] = get_event_picture(post_dict['id'],dir='docs')
				elif "shared" in post_dict['story'] :

					post_dict['message'] = '<b>' + post_dict['story'] + '</b>' + '\n\n' + get_shared_post(post_dict['id']) 

			  #  print (post_dict['message'])
			else :
				if not "message" in post_dict :
					post_dict['message'] = get_video(post_dict['id'])

			
	data.extend(old_data)
	data.sort(key=lambda x: parse(x['created_time']), reverse=True)

	json.dump(data, open('docs/{}.json'.format(page_id), 'w'))

	return data


def remove_duplicates(data):
	uniq_data = []
	for item in data:
		if item not in uniq_data:
			uniq_data.append(item)

	return uniq_data


def prettify_date(data):
	for item in data:
		date = parse(item['created_time'])
		tzlocal = tz.gettz('Asia/Kolkata')
		local_date = date.astimezone(tzlocal)
		item['real_date'] = local_date.strftime('%d-%m-%Y')
		item['real_time'] = local_date.strftime('%I:%M%p')
	return data


def get_aggregated_feed(pages):
	"""
	Aggregates feeds give a list of pages and their ids.

	Input: A list of tuples
	Output: Combined list of posts sorted by timestamp
	"""
	data = list()
	for page_name, _id in pages:
		page_data = get_feed(_id)
		for data_dict in page_data:
			data_dict['source'] = page_name
		data.extend(page_data)

	data.sort(key=lambda x: parse(x['created_time']), reverse=True)
	return data


if __name__ == "__main__":
	f=open("hist.txt","w")
	f.write(str(random()))
	news_pages = [('The Scholar\'s Avenue', 'scholarsavenue'),
			('Awaaz IIT Kharagpur', 'awaaziitkgp'),
			('Technology Students Gymkhana', 'TSG.IITKharagpur'),
			('Technology IIT KGP', 'iitkgp.tech'),('Kharagpur Open Source Society','kossiitkgp'),
			('Metakgp', 'metakgp'),('Kharagpur RoboSoccer Students\' Group','krssg'),
			('Technology Robotix Society','robotixiitkgp'),('Swarm Robotics','swarmroboticskgp'),
			('Kharagpur Data Analytics Group','kgpdag'), ('Autonomous Ground Vehicle','agvkgp'),
			('Aerial Robotics Kharagpur','aerialroboticskgp'),('TeamKART','TeamKART'),('Debating Society','kgpdebsoc'),
			('Technology Literary Society','tlsiitkgp'),('AIESEC','aieseciitkgp'),('Student Welfare Group','SWGIITKGP'),
			('The KGPian Game Theory Society','The.KGTS'),('Electric Vehicle Group','EVPIITKGP'),('Business Club','bclubkgp'),
			('Communiqué','communique.iitkgp'),('International Relations Cell','IRCIITKGP'),
			('Quiz Club','iitkgp.quizclub'),('Branding And Relations Cell','barciitkgp'),('Alumni Cell','iitkgp.alumnicell'),
			('Entrepreneurship Cell','ecell.iitkgp'),('Gopali Youth Welfare Society','gyws.iitkgp'),
			('Kshitij','ktj.iitkgp'),('Spring Fest','springfest.iitkgp'),('CodeClub','CodeClub.IITKGP'),('ProDex','prodex.iitkgp'),
			('Director IIT Kharagpur','director.iitkgp')]
	for_later = ['Cultural-IIT-Kharagpur']

	data = get_aggregated_feed(news_pages)
	data = remove_duplicates(data)
	data = prettify_date(data)

	json.dump(data, open('docs/feed.json', 'w'))
	write_html(data, 'docs/index.html')
	tz = pytz.timezone('Asia/Kolkata')
	now =  datetime.now(tz)
	minutes = now.minute
	if (len(str(minutes))==1):
		text = "Last updated: "+str(now.day)+"-"+str(now.month)+"-"+str(now.year)+", "+str(now.hour)+":0"+str(minutes)+" IST"
	else:
		text = "Last updated: "+str(now.day)+"-"+str(now.month)+"-"+str(now.year)+", "+str(now.hour)+":"+str(minutes)+" IST"
	fn=open("docs/index.html","r")
	fo=open("docs/indext.html","w")
	all_text = fn.read()
	all_text = all_text.replace(' <!-- Time stamp here -->',text)
	fo.write(all_text)
	os.system("mv docs/indext.html docs/index.html")

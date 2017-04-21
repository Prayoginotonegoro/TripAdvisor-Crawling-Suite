#!/usr/bin/python3
# -*- coding:utf8 -*-
import common
from common import HOTEL_ID, HOTEL_URL, SLEEP_TIME
from common import HOTEL_PER_PAGE, SNIPPET_THREAD_NUM
from os.path import isfile
import re
import math
import threading
import queue
import time


lock = threading.Lock()


def find_hotel_ids(soup_container):
    page_hotels = []
    for link in soup_container.find_all('div', id=re.compile('^hotel_')):
        if link.has_attr('id'):
            hid = link['id'][6:]
            snippet = link.select('.metaLocationInfo')[0]
            url = snippet.select('.listing_title')[0].find('a')['href']
            page_hotels.append({HOTEL_ID: hid, HOTEL_URL: url[1:]})
    return page_hotels


def update_hotel_ids(new_pairs, pair_list):
    def has_pair(id_value):
        return id_value in [x[HOTEL_ID] for x in pair_list]

    for new_pair in new_pairs:
        if not has_pair(new_pair[HOTEL_ID]):
            pair_list.append(new_pair)
        else:
            # duplicate hotel id
            pass


def find_max_page(soup_container):
    div = soup_container.find('div', class_='pageNumbers')
    num = div.find_all('a')[-1]
    return int(num['data-page-number'])


def calc_max_page(soup_container):
    return math.ceil(find_num_hotels(soup_container) / HOTEL_PER_PAGE)


def find_num_hotels(soup_container):
    div = soup_container.find('fieldset', id='p13n_PROPTYPE_BOX')
    num = div.find('span', class_='tab_count').text
    num = int(re.sub('\D', '', num))
    return num


def gather_hotels(title):
    while True:
        print('[worker {}] running'.format(title))
        pid = que.get()
        if pid is None:
            print('[worker {}] shutting down'.format(title))
            break
        paras = '&'.join([
            'seen=0', 'sequence=1', 'geo=' + locID,
            'requestingServlet=Hotels', 'refineForm=true',
            'hs=', 'adults=2', 'rooms=1',
            'o=a' + str(pid * HOTEL_PER_PAGE),
            'pageSize=&rad=0', 'dateBumped=NONE',
            'displayedSortOrder=popularity'])
        pageURL = ''.join([seed, '?', paras])
        print('[page {}] {}'.format(pid+1, pageURL))
        hotels = find_hotel_ids(common.load_soup_online(pageURL))
        time.sleep(SLEEP_TIME)
        if len(hotels) < HOTEL_PER_PAGE and pid < numPage - 1:
            que.put(pid)
        elif pid == numPage - 1 \
                and len(hotels) < numHotel % HOTEL_PER_PAGE:
            que.put(pid)
        else:
            with lock:
                update_hotel_ids(hotels, hidPairs)
                print('\t#{}, totaling {}'.format(pid, len(hidPairs)))
                common.write_binary('hids.txt', hidPairs)
        que.task_done()


seed = input('url: ')
locID = re.sub('\D', '', seed)
locName = seed[seed.index(locID) + len(locID) + 1:seed.rindex('-')]
print('location: {} ({})'.format(locName.replace('_', ' '), locID))
soup = common.load_soup_online(seed)
numPage = find_max_page(soup)
numHotel = find_num_hotels(soup)
print('{} hotels in {} pages'.format(numHotel, numPage))

hidPairs = common.read_binary('hids.txt') if isfile('hids.txt') else []
print('{} hotels in the local list'.format(len(hidPairs)))

# collecting hotel ids might take multiple iterations
while len(hidPairs) < numHotel:
    que = queue.Queue()

    threads = []
    for j in range(SNIPPET_THREAD_NUM):
        t = threading.Thread(
            target=gather_hotels, args=(str(j + 1))
        )
        t.start()
        threads.append(t)

    # push items into the queue
    [que.put(x) for x in
     range(math.ceil(len(hidPairs) / HOTEL_PER_PAGE), numPage)]

    # block until all tasks are done
    que.join()

    # stop workers
    for k in range(SNIPPET_THREAD_NUM):
        que.put(None)
    for t in threads:
        t.join()

print('all hotel ids are ready'.format(len(hidPairs)))

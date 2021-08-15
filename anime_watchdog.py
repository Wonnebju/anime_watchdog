# -*- coding: utf-8 -*-
"""
Created on Freitag August 13 12:40 2021

notifier for new episodes on shared lists from gogoanime

@author: Wonnebju
"""

import requests
from bs4 import BeautifulSoup
import jsonpickle
import re
import datetime
import os

############ Your shared list url ############
shared_list = "YOUR SHARED LIST URL"

class Log:
    def __init__(self, path="", name="log", timestamp=True, time_format="%d-%m-%Y %H:%M:%S"):
        self.path = path
        self.name = name
        self.timestamp = timestamp
        self.time_format = time_format

    def append(self, line):
        with open(self.path + self.name + ".txt", "a", encoding="utf-8") as log_file:
            if self.timestamp:
                stamp = datetime.datetime.now()
                line = stamp.strftime(self.time_format) + ": " + line
            log_file.write(line + "\n")


class Animu:

    def __init__(self, name="Animu", ep=0, url="url", eurl="eurl", turl="turl", tname="tname",
                 time_format="%d-%m-%Y %H:%M:%S"):
        self.name = name
        self.episode = ep
        self.url = url
        self.episode_url = eurl
        self.thumb_url = turl
        self.thumb_name = tname
        now = datetime.datetime.now().strftime(time_format)
        self.created = now
        self.modified = now

    def __str__(self):
        return "name={}, latest={}, url={}, eurl={}, created={}, modified={}".format(self.name,
                                                                                     self.episode,
                                                                                     self.url,
                                                                                     self.episode_url,
                                                                                     self.created,
                                                                                     self.modified)


def win_notification(ntype, anime_name, thumb="", url=""):
    import winrt.windows.ui.notifications as notifications
    import winrt.windows.data.xml.dom as dom

    app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'

    # create notifier
    nManager = notifications.ToastNotificationManager
    notifier = nManager.create_toast_notifier(app)

    if thumb != "":
        thumb = "<image placement=\"Hero\" src=\"" + thumb + "\"/>"
    if url != "":
        url = """
        <action
          content = "View"
          arguments = "{}"
          activationType = "protocol" />
        """.format(url)

    tString = """
      <toast>
        <visual>
          <binding template='ToastGeneric'>
            <text>{}</text>
            <text>{}</text>
            {}
          </binding>
        </visual>
        <actions>
          {}
          <action
            content="Delete"
            arguments="action=delete"/>
        </actions>        
      </toast>
    """.format(anime_name, ntype, thumb, url)

    xDoc = dom.XmlDocument()
    xDoc.load_xml(tString)

    notifier.show(notifications.ToastNotification(xDoc))


if __name__ == "__main__":

    log = Log()
    time_format = "%d-%m-%Y %H:%M:%S"
    base_url = "https://gogoanime.pe"

    # thumbnail dir
    try:
        os.mkdir('thumbs')
    except FileExistsError:
        pass

    # restore db
    with open("animus.json", "r", encoding="utf-8") as infile:
        try:
            animus = jsonpickle.decode(infile.read())
        except:
            animus = {}

    # get current list
    r = requests.get(shared_list)
    s = r.text
    with open("tmp.html", "w", encoding="utf-8") as outfile:
        outfile.write(s)

    with open("tmp.html", "r", encoding="utf-8") as infile:
        soup = BeautifulSoup(infile, 'html.parser')
        tmp = soup.find("div", {"class": "article_bookmark"})
        b = True
        now = datetime.datetime.now().strftime(time_format)
        for animu in soup.find_all("div", {"class": "column_left_1"}):
            if b:  # skip first entry
                b = False
                continue
            first_a = animu.a
            second_a = animu.find("a", {"class": "episode"})
            anime_name = first_a.text.strip()
            episode = re.findall("Episode.(.+)", second_a.text)[0]

            # falls neuer eintrag
            if anime_name not in animus.keys():
                thumb_url = re.findall("url\('(.+)'\)", first_a.div['style'])[0]
                thumb_extension = re.findall(".+(\....)$", thumb_url)[0]
                thumb_name = "".join(x for x in anime_name if x.isalnum()) + thumb_extension

                animus[anime_name] = Animu(name=anime_name,
                                           ep=episode,
                                           url=base_url + first_a['href'],
                                           eurl=base_url + second_a['href'],
                                           turl=thumb_url,
                                           tname=thumb_name)

                response = requests.get(thumb_url)
                with open("thumbs\\" + thumb_name, 'wb') as img:
                    img.write(response.content)

                ntype = "was added to your list!".format(anime_name)
                log.append("New Anime: " + anime_name)
                thumb_path = os.getcwd() + "\\thumbs\\" + animus[anime_name].thumb_name
                win_notification(ntype, anime_name, thumb_path, base_url + first_a['href'])

            # falls modifiziert (neue episode/n)
            elif animus[anime_name].episode < episode:
                diff = int(episode) - int(animus[anime_name].episode)
                if diff > 1:
                    ntype = "New Episodes {}-{}".format(int(animus[anime_name].episode) + 1, episode)
                else:
                    ntype = "New Episode {} ".format(episode)
                animus[anime_name].episode = episode
                animus[anime_name].episode_url = base_url + second_a['href']
                animus[anime_name].modified = now

                log.append(ntype + " " + anime_name)
                thumb_path = os.getcwd() + "\\thumbs\\" + animus[anime_name].thumb_name
                win_notification(ntype, anime_name, thumb_path, animus[anime_name].episode_url)

            # ansonsten nichts aendern

    with open("animus.json", "w", encoding="utf-8") as outfile:
        outfile.write(jsonpickle.encode(animus))

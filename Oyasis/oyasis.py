
import requests
from bs4 import BeautifulSoup
import random
import json
from SeleniumScript.selenium_script import SeleniumScript as sel_script
import configparser


class Ini:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.username = self.config['WEBLATE']['username']
        self.password = self.config['WEBLATE']['password']
        self.url = self.config['WEBLATE']['url']

    def set_password(self, password):
        self.password = password

    def set_username(self, username):
        self.username = username

    @staticmethod
    def get_url(self):
        return self.url


class Session:
    def __init__(self, **kwargs):
        self.__ini = kwargs["ini"]
        head = {'Content-Type': 'application/x-www-form-urlencoded', \
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
        login_details = {"username": self.__ini.username, "password": self.__ini.password}
        url = self.__ini.url + "/accounts/login/"
        with requests.Session() as s:
            # open the login page
            r = s.get(url)
            # Get the csrf-token from input tag
            soup = BeautifulSoup(r.text, "lxml")
            # Get the page cookie
            cookie = r.cookies
            self.cookies = cookie
            csrf_token = soup.select_one('input[name="csrfmiddlewaretoken"]')['value']
            # Set CSRF-Token
            head['X-CSRF-Token'] = csrf_token
            head['X-Requested-With'] = 'XMLHttpRequest'
            head['Referer'] = self.__ini.url
            self.head = head
            login_details["csrfmiddlewaretoken"] = csrf_token
            # request login
            r = s.post(url, cookies=cookie, data=login_details, headers=head)
            self.session = s

    def getSession(self):
        return self.session

    def getCookies(self):
        return self.cookies


class Tafsiri:
    def __init__(self, **kwargs):
        self.__session = kwargs["session"]
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.__url = self.config['WEBLATE']['url']

    def get_all_components(self):
        weblate_session = self.__session.getSession()
        weblate_api_response = weblate_session.get(self.__url + "/api/components/?format=json")
        components_dict = json.loads(weblate_api_response.text)
        try:
            components_list = components_dict["results"]
        except Exception as e:
            print(f"having trouble working on {weblate_api_response.url} that returned {weblate_api_response.text}")
            components_list = []
        while components_dict["next"] is not None:
            weblate_api_response = weblate_session.get(components_dict["next"])
            components_dict = json.loads(weblate_api_response.text)
            components_list_next_page = components_dict["results"]
            components_list += components_list_next_page
        return components_list

    def select_component(self):
        incomplete_components = self.get_incomplete_components()
        if incomplete_components.__len__() == 0:
            return None
        else:
            return random.choice(incomplete_components)

    def get_incomplete_components(self):
        incomplete_components = []
        print("about to loop through all components")
        for component in self.get_all_components():
            if self.get_translation_progress(component["statistics_url"]) is not None and self.get_translation_progress(
                    component["statistics_url"]) < 100.0:
                incomplete_components.append(component)
        return incomplete_components

    def get_translation_progress(self, component_statistics_url):
        weblate_session = self.__session.getSession()
        weblate_api_response = weblate_session.get(component_statistics_url)
        statistics_dict = json.loads(weblate_api_response.text)
        try:
            progress_results_per_languages = statistics_dict["results"]
        except Exception as e:
            print(f"having trouble with {component_statistics_url}")
            return None
        for progress in progress_results_per_languages:
            if progress["code"] == 'sw':
                return progress["translated_percent"]
        return None

    def get_max_offset(self, component_url):
        url_for_untranslated_strings = component_url.replace("/projects/", "/translate/") + "sw/?type=nottranslated"
        weblate_session = self.__session.getSession()
        weblate_request = weblate_session.get(url_for_untranslated_strings)
        beautifulsoup_object = BeautifulSoup(weblate_request.text, "lxml")
        max_offset = int(beautifulsoup_object.select_one('input[id="id-goto-number"]')["max"])
        return max_offset

    def get_random_string(self):
        component = self.select_component()
        if component is None:
            return "No untranslated strings"
        component_url = component["web_url"]
        url_for_untranslated_strings = component_url.replace("/projects/", "/translate/") + "sw/?type=nottranslated"
        max_offset = self.get_max_offset(component_url)
        random_offset = random.randrange(1, max_offset)
        result = self.get_untranslated_string(component, url_for_untranslated_strings, random_offset)
        return result

    def get_all_untranslated_strings(self):
        strings_file = open("untranslated_strings.txt", "r")
        strings_file_object = StringsFile()
        for component in self.get_incomplete_components():
            component_url = component["web_url"]
            url_for_untranslated_strings = component_url.replace("/projects/", "/translate/") + "sw/?type=nottranslated"
            max_offset = self.get_max_offset(component_url)
            print("currently looking into " + component["slug"])
            for offset in range(max_offset):
                offset = offset + 1
                untranslated_strings_dict = self.get_untranslated_string(component, url_for_untranslated_strings,
                                                                         offset)
                del untranslated_strings_dict['cookies']
                strings_file_object.write_untranslated_strings_file(untranslated_strings_dict)
        strings_file.close()
        strings_file = open(self.config['PERSISTENCE']['untranslated_strings_file_path'], "r")
        print(strings_file.read())
        strings_file.close()
        return strings_file.read()

    def get_untranslated_string(self, component, url_for_untranslated_strings, offset):
        weblate_session = self.__session.getSession()
        weblate_request = weblate_session.get(f"{url_for_untranslated_strings}&offset={offset}")
        beautifulsoup_object = BeautifulSoup(weblate_request.text, "lxml")
        form = beautifulsoup_object.select_one('form[class="translation-form translator"]')
        formelbs = BeautifulSoup(str(form), "lxml")
        endpoint = self.__url + form['action']
        random_string = formelbs.select_one('button[class="btn btn-link btn-xs pull-right flip"]')[
            'data-clipboard-text']
        checksum = formelbs.select_one('input[name="checksum"]')['value']
        cookie = weblate_request.cookies
        string_dict = {"endpoint": endpoint, \
                       "cookies": cookie, \
                       "checksum": checksum, \
                       "RandString": random_string, \
                       "component": component["slug"], \
                       "offset": offset \
                       }
        return string_dict

    def translate(self, **kwargs):
        todo = kwargs["todo"]
        translation = kwargs["translation"]
        url = todo["endpoint"]
        print("making submission to " + url + "\ncookies: "+str(todo["cookies"].items()))
        try:
            cookie = todo["cookies"].items()[0]
        except IndexError as e:
            cookie = ("sessionid",self.config['WEBLATE']['fallback_cookie'])
        checksum = todo["checksum"]
        translation_box_xpath = self.set_translation_box_xpath(checksum)
        selenium_script = sel_script()
        selenium_script.navigate_page(url, cookie)
        print("presently passing " + url + " to selenium as url")
        selenium_script.set_translation(translation_box_xpath, translation)
        selenium_script.send_translation("div.panel:nth-child(1) > div:nth-child(3) > button:nth-child(1)")

    @staticmethod
    def set_translation_box_xpath(checksum):
        return '//*[@id="id_' + checksum + '_0"]'


class StringsFile:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.filename = self.config['PERSISTENCE']['untranslated_strings_file_path']
        self.existing_phrase_endpoints = self.get_existing_phrase_endpoints()

    def get_file_contents(self):
        try:
            english_string_obj_file = open(self.filename, 'r')
        except FileNotFoundError as fileError:
            return []
        english_string_obj_file_contents = english_string_obj_file.readlines()
        return english_string_obj_file_contents

    def get_existing_phrase_endpoints(self):
        endpoints_list = []
        all_file_contents = self.get_file_contents()
        for entry in all_file_contents:
            try:
                json_obj = json.loads(entry.strip().replace("'",'"'))
                endpoints_list.append(json_obj['endpoint'])
            except Exception as e:
                continue
        return endpoints_list

    def write_untranslated_strings_file(self, string_object):
        untranslated_strings_file = open(self.filename,'a')
        if string_object['endpoint'] not in self.existing_phrase_endpoints:
            untranslated_strings_file.write(str(string_object))
            untranslated_strings_file.write('\n')
            print('adding '+str(string_object))
        else:
            print(str(string_object)+' is already in file')

=======
import requests
import lxml
from bs4 import BeautifulSoup
import re
import random
class Site:
    url = "https://tafsiri.swahilinux.org"

class Ini(Site):
    def __init__(self,**kwargs):
        self.username = kwargs["username"]
        self.password = kwargs["password"]
        self.url = super().url
    def set_password(self,password):
        self.password = password
    def set_username(self,username):
        self.username = username
    @staticmethod
    def get_url(self):
        return self.url

class Session:
    def __init__(self,**kwargs):
        self.__ini = kwargs["ini"]
        head= { 'Content-Type':'application/x-www-form-urlencoded',\
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
                AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
        login_details ={"username":self.__ini.username,"password":self.__ini.password}
        url = self.__ini.url+"/accounts/login/"
        with requests.Session() as s:
            #open the login page
             r = s.get(url)
             # Get the csrf-token from input tag
             soup = BeautifulSoup(r.text,"lxml")
             # Get the page cookie
             cookie = r.cookies
             self.cookies = cookie
             csrf_token = soup.select_one('input[name="csrfmiddlewaretoken"]')['value']
             # Set CSRF-Token
             head['X-CSRF-Token'] = csrf_token
             head['X-Requested-With'] = 'XMLHttpRequest'
             head['Referer'] = self.__ini.url
             self.head = head
             login_details["csrfmiddlewaretoken"] = csrf_token
             #request login
             r = s.post(url, cookies=cookie, data=login_details, headers=head)
             self.session = s
             #see if logged in
             #r = s.get(self.__ini.url)
             #print(r.text)
            #  soup = BeautifulSoup(r.text,"lxml")
            #  link = soup.find("a",{"id":"user-dropdown"})
            #  print(link)
    def getSession(self):
        return self.session
class Project:
    def __init__(self,title,endpoint):
        self.__title = title
        self.__endpoint = endpoint
    def set_title(self,title):
        self.__title = title
    def get_title(self):
        return self.__title
    def get_endpoint(self):
        return self.__endpoint
    def set_endpoint(self,endpoint):
        self.__endpoint = endpoint
class Tafsiri(Site):
    def __init__(self,**kwargs):
        self.__session = kwargs["session"]
        self.__url = super().url

    def getProjects(self):
        s = self.__session.getSession()
        rqst = s.get(self.__url)
        soup = BeautifulSoup(rqst.text,"lxml")

        projects_ul = soup.find("ul",{"class":"dropdown-menu"})
        #pattern_li_txt = re.compile("<a>(.*)*</a>")
        projects = "".join([str(x.findAll(r"a"))[1:-1]  for x in projects_ul.findAll(r"li")][:-3])
        soup = BeautifulSoup(projects,"lxml")
        projects_list = [{"endpoint":a['href'],"title":a.contents[0]} for a in soup.find_all('a')]
        self.__projects = projects_list

        return projects_list
    def selectProject(self,title):
        projects = self.getProjects()
        Dict = [{"title":x["title"],"endpoint":x["endpoint"]} for x in projects if x["title"] == title][0]
        selected_project = Project(Dict["title"],Dict["endpoint"])
        self.project = selected_project
    def selectRandomProject(self):
        projects = self.getProjects()
        Dict = random.choice(projects)
        selected_project = Project(Dict["title"],Dict["endpoint"])
        self.project = selected_project
    def getRandomString(self):
        project = self.project
        url = self.url+"/translate"+project.get_endpoint()[9:]
        url = url+ project.get_endpoint()[10:]+"sw/?type=nottranslated"
        s = self.__session.getSession()
        rqst = s.get(url)
        soup = BeautifulSoup(rqst.text,"lxml")
        form = soup.select_one('form[class="translation-form translator"]')
        cookie = rqst.cookies
        csrf_token = soup.select_one('input[name="csrfmiddlewaretoken"]')['value']
        # Set CSRF-Token
        head = {}
        head['X-CSRF-Token'] = csrf_token
        head['X-Requested-With'] = 'XMLHttpRequest'
        head['Referer'] = url
        #get a random offset
        try:
            offset = int(soup.select_one('input[id="id-goto-number"]')["max"])
            random_offset = random.randrange(1,offset)
            rqst = s.get(f"{url}&offset={random_offset}")
            soup = BeautifulSoup(rqst.text,"lxml")
            form = soup.select_one('form[class="translation-form translator"]')
            formelbs = BeautifulSoup(str(form),"lxml")
            endpoint = form['action']
            content_sum = formelbs.select_one('input[name="contentsum"]')['value']
            translation_sum = formelbs.select_one('input[name="translationsum"]')['value']
            csrf_token = formelbs.select_one('input[name="csrfmiddlewaretoken"]')['value']
            ranstring = formelbs.select_one('button[class="btn btn-link btn-xs pull-right flip"]')['data-clipboard-text']
            checksum =  formelbs.select_one('input[name="checksum"]')['value']
            result = {"endpoint":endpoint,\
                    "cookies":cookie,\
                    "header":head,\
                    "checksum":checksum,\
                    "contentsum":content_sum,\
                    "csrfmiddlewaretoken":csrf_token,\
                    "RandString":ranstring,\
                    "translationsum":translation_sum,\
                    "offset":random_offset\
                                }
        except TypeError:
            self.getRandomString()

        return result
        #print(content_sum,translation_sum,csrf_token,endpoint,offset,ranstring
    def translate(self,**kwargs):
        todo = kwargs["todo"]
        translation = kwargs["translation"]
        session = self.__session.getSession()
        url = self.url+todo["endpoint"]
        head = todo["header"]
        cookies = todo["cookies"]
        payload = {"csrfmiddlewaretoken":todo["csrfmiddlewaretoken"],\
                    "content":translation,\
                    "checksum":todo["checksum"],\
                    "fuzzy":"",\
                    "contentsum":todo["contentsum"],\
                    "translationsum":todo["translationsum"],\
                    "review":"0",\
                    "save":""}
        head["Referer"] = url
        post = session.post(url,data=payload,cookies=cookies,headers=head)
        # with open("o.htm","w") as m:
        #     print(post.text) 







    


        



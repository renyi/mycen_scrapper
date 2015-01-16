#!/usr/bin/env python

import logging
import json
import re
import requests
from bs4 import BeautifulSoup
from pprint import pprint

logger = logging.getLogger(__name__)

GOV_HOSP_URL = "http://www.mycen.com.my/malaysia/hospital_government.html"
PRI_HOSP_URL = "http://www.mycen.com.my/malaysia/hospital_private.html"
AMBULANCE_URL = "http://www.mycen.com.my/malaysia/ambulance.html"


class Base(object):
    """Base scrapper for http://mycen.com.my/.
    """
    url = None
    dumpdata = False
    raw_filename = None # raw HTML
    json_filename = None # raw JSON or Django Fixture

    def __init__(self, *args, **kwargs):
        url = kwargs.get("url", None)
        dumpdata = kwargs.get("dumpdata", None)
        raw_filename = kwargs.get("raw_filename", None)
        json_filename = kwargs.get("json_filename", None)

        if url:
            self.url = url

        if dumpdata:
            self.dumpdata = dumpdata

        if raw_filename:
            self.raw_filename = raw_filename

        if json_filename:
            self.json_filename = json_filename

    def get_html(self):
        """Get html.
        """
        if not self.url:
            return None

        url = self.url
        dumpdata = self.dumpdata
        filename = self.raw_filename

        if not filename:
            # Get filename from url
            filename = url.split('/')[-1]
            logger.debug(filename)

        response = requests.get(url)

        if dumpdata:
            f = open(filename, 'w')
            try:
                f.write(response.text)
            except Exception, e:
                logger.error("%s" % e)
            finally:
                f.close()

        return response.text

    def parse(self):
        """Data parser.
        """
        html = self.get_html()

        if not html:
            return

        soup = BeautifulSoup(html, "lxml")

        if not soup:
            return

        # Find checkpoint by text "Place your"
        result = soup.findAll(text=re.compile("Place your"))

        if not result:
            return

        # The table we need
        table = result[0].find_parent("table").find_next_sibling("table")

        # Find data
        rows = table.find_all("tr")
        for r in rows:
            cols = r.find_all("td")
            data = cols[0].get_text()
            break

        # Clean data
        lines = data.split('\n')
        lines = [line.strip() for line in lines]
        lines = '\n'.join(lines)
        lines = lines.split('\n\n')

        return lines

    def to_json(self, dump_data=True):
        """Generic json
        """
        lines = self.parse()

        cleaned_data = []
        for i, line in enumerate(lines):
            data = line.split('\n')
            cleaned = {
                i: {
                    "name": "",
                    "address": "",
                    "contact": "",
                    "website": "",
                }
            }

            for j, d in enumerate(data):
                # Uncomment to inspect raw data
                # print j
                # pprint(d)

                if j == 0:
                    cleaned[i]["name"] = d

                elif "Tel: " in d:
                    for _ in d.split(','):
                        if "Tel: " in _:
                            cleaned[i]["contact"] = _.replace("Tel: ", "")

                elif "http" in d:
                    cleaned[i]["website"] = d

                elif cleaned[i]["contact"] == "" and \
                     not "As featured in" in d:

                    if cleaned[i]["address"]:
                        cleaned[i]["address"] += " %s" % d
                    else:
                        cleaned[i]["address"] = d

            cleaned_data.append(cleaned)

        # pprint(cleaned_data)

        if self.json_filename and dump_data:
            with open(self.json_filename, 'w') as outfile:
                json.dump(cleaned_data, outfile)
        else:
            return cleaned_data

    def to_django(self, model, dump_data=True):
        """Django fixture.

        Parameters:
            model: "model.model".
        """
        json_list = self.to_json(False)

        if not json_list:
            return

        cleaned_data = []
        for i in json_list:
            for k in i.keys():
                data = i[k]

                cleaned = {
                    "fields": {
                        "name": data["name"],
                        "address": data["address"],
                        "contact": data["contact"],
                        "website": data["website"],
                    },
                    "model": model,
                    "pk": k,
                }
            cleaned_data.append(cleaned)

        if self.json_filename and dump_data:
            with open(self.json_filename, 'w') as outfile:
                json.dump(cleaned_data, outfile)
        else:
            return cleaned_data


class GovHosp(Base):
    """Government Hospital Scrapper
    """
    url = GOV_HOSP_URL
    type = 0

    def to_json(self, dump_data=True):
        cleaned_data = super(GovHosp, self).to_json(False)

        if not cleaned_data:
            return

        # # Append type to clean_data
        new_cleaned_data = []
        for i in cleaned_data:
            for k in i.keys():
                i[k]["type"] = self.type
            new_cleaned_data.append(i)

        # pprint(new_cleaned_data)

        if self.json_filename and dump_data:
            with open(self.json_filename, 'w') as outfile:
                json.dump(new_cleaned_data, outfile)
        else:
            return new_cleaned_data

    def to_django(self, model, dump_data=True):
        json_list = self.to_json(False)

        if not json_list:
            return

        cleaned_data = []
        for i in json_list:
            for k in i.keys():
                data = i[k]
                cleaned = {
                    "fields": {
                        "name": data["name"],
                        "address": data["address"],
                        "contact": data["contact"],
                        "website": data["website"],
                        "type": self.type
                    },
                    "model": model,
                    "pk": k,
                }
            cleaned_data.append(cleaned)

        if self.json_filename and dump_data:
            with open(self.json_filename, 'w') as outfile:
                json.dump(cleaned_data, outfile)
        else:
            return cleaned_data


class PriHosp(GovHosp):
    """Private Hospital Scrapper
    """
    url = PRI_HOSP_URL
    type = 1


class AmServ(Base):
    """Ambulance Service Scrapper
    """
    url = AMBULANCE_URL


if __name__ == '__main__':
    g = GovHosp(json_filename='../fixtures/hospitals.json')
    data = g.to_django("hospital.hospital")
    # pprint(data)

    p = PriHosp(json_filename='../fixtures/private_hospitals.json')
    data = p.to_django("hospital.hospital")
    # pprint(data)

    a = AmServ(json_filename="../fixtures/ambulanceservices.json")
    data = a.to_django("hospital.ambulanceservice")
    # pprint(data)

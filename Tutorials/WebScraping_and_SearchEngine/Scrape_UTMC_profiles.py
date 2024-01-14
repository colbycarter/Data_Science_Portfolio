# the purpose of this program is to scrape the profiles of all the UTMC doctors and save the structured dataset for model training

# import libraries
import sys

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import re

import time

import numpy as np
import pandas as pd


# UTMC doctor-finder class
class UTMC_doc_profile_scraper:

    def __init__(self, finder_ULR, doctor_count):
        """save main doctor-finder URL and get soup"""
        self.finder_ULR = finder_ULR
        self.doctor_count = doctor_count
        
        # get main soup
        self.finder_page = requests.get(self.finder_ULR).text

    def print_URLs(self, soup):
        """add next URL to the list of doctor profile URLs"""
        URL_list = []
        doctor_soup = soup.find_all('p', class_='text-lg font-bold')  # updated
        for doctor in doctor_soup:
            name = doctor.find('a', class_="relative")  #updated
            URL_list+=[name['href']]
        return URL_list

    def doctor_URL_loop(self, docs_per_page=6, sleep=4.0):
        """click through all pages of doctor-finder and add doctor profile URLs to list"""
        start = time.time()

        # install Chrome driver, go to starting page
        driver = webdriver.Chrome(ChromeDriverManager().install())
        driver.get(self.finder_ULR)

        # get page source
        # finder_page = driver.page_source
        finder_soup = BeautifulSoup(self.finder_page, "html.parser")

        # init doctor URLs
        self.doctor_URLs = []
        # self.doctor_URLs += self.print_URLs(finder_soup)

        # get number of clicks
        clicks = int(np.ceil((doc_count-docs_per_page)/docs_per_page))

        # click Load More until showing all doctors
        for i in range(clicks):
            # print(i)

            # find and click next button
            next_button = driver.find_element_by_css_selector(".button.unstyle")  # why the periods? don't know
            driver.execute_script("arguments[0].click();", next_button);

            # pause to load next page?
            time.sleep(sleep)

        # get new page soup & URLs
        next_page = driver.page_source
        next_doctor_soup = BeautifulSoup(next_page, 'html.parser')
        
        # update URL list
        self.doctor_URLs += self.print_URLs(next_doctor_soup)

        driver.quit()
        # self.page = page
        end = time.time()
        # print("Pages:", self.page-1)
        print((end-start)/60, "mins")
        return self

    def scrape_doc_info(self):
        """for each doctor profile, scrape and format key info"""
        start = time.time()

        # full loop
        for i, doc_url in enumerate(self.doctor_URLs):
            # init single doctor dict
            doc_dict = {}

            # get soup
            doctor_page = requests.get(doc_url).text
            doctor_soup = BeautifulSoup(doctor_page, "html.parser")

            # doc name
            heading = doctor_soup.find('div', id="doctor-name-column").find('h2').string.split(",")
            doc_dict["Name"] = [heading[0]]

            # URL
            doc_dict["Web_URL"] = [doc_url]

            # education (from doc-name-column)
            doc_dict["Education"] = [heading[1]]

            # Specialty
            specialtyList = ''
            for spec in doctor_soup.find('div', id='doctor-name-column').find_all('p', class_='large'):
                specialtyList += spec.string.strip()
            doc_dict["Specialty"] = [specialtyList.strip()]

            # location
            location = doctor_soup.find('p', class_='large doctor-location')
            if location != None:
                zip_code = re.search(r'\d{5}', location.get_text())
                if zip_code != None:
                    doc_dict["Zip"] = [zip_code.group()]

            # free form bio/interest
            h5_tags = doctor_soup.find_all('h5')  # h5s contain the bio details
            for tag in h5_tags:
                next_element = tag.find_next_sibling().get_text(strip=True)

                if tag.string == "Gender":
                    doc_dict["Gender"] = [next_element]

                elif tag.string == "Languages Spoken:":
                    languages = next_element.replace("English,", "").strip()
                    # print(languages)
                    doc_dict["Language"] = languages

                elif tag.string == "Personal Interests:":
                    doc_dict["Personal"] = [next_element]

                elif tag.string == "Research Interests:":
                    doc_dict["Research"] = [next_element]

                elif tag.string == "Clinical Interests:":
                    doc_dict["Clinical"] = [next_element]

            # append to doctor table
            if i == 0:
                doctorDF = pd.DataFrame.from_dict(doc_dict)
            else:
                newDF = pd.DataFrame.from_dict(doc_dict)
                doctorDF = pd.concat([doctorDF, newDF])

        self.doctorDF = doctorDF.reset_index().drop(["index"], axis=1)
        print("Shape:", self.doctorDF.shape)

        end = time.time()
        print((end-start)/60, "mins")
        return self.doctorDF

    def save_dataset(self):
        print(self.doctorDF["Specialty"].describe())
        self.doctorDF.to_csv(
            "C:/Users/Colby/Documents/GitHub/health_finder/my-health-agency/Python/Output/Data/UTMC_doctor_profiles.csv",
            index=False)


def main():
    # Get the command-line argument
    url = sys.argv[1]

    # Create an instance of UTMC_doc_profile_scraper
    scraper = UTMC_doc_profile_scraper(url)

    # Call methods
    # get list of doctor profile URLs
    print("Scrape URLs:")
    scraper.doctor_URL_loop()

    # scrape each profile and add to dataset
    print("Get profiles:")
    scraper.scrape_doc_info()

    # print summary
    print("Summary:")
    scraper.save_dataset()


if __name__ == "__main__":
    main()

# beautiful soup doctor-finder page - for command line arg
# finder_ULR = 'https://www.utmedicalcenter.org/medical-care/medical-services/find-a-doctor/'

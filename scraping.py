"""
author: Emile Johnston
date: 2024-11-01

This script is for scraping metadata from the TU Wien repository.
"""

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from io import BytesIO
from PyPDF2 import PdfReader
import time
import json
# import pandas as pd

# Define constants
DOMAIN = "https://repositum.tuwien.at"
MAIN_PAGE = "https://repositum.tuwien.at/simple-search?location=theses&query=&crisID=&relationName=&filter_field_1=dateIssued&filter_type_1=equals&filter_value_1=%5B2020+TO+2024%5D&rpp=50&sort_by=bi_sort_2_sort&order=desc&submit_search=Update"
CRAWL_DELAY = 5  # 5 seconds as requested by https://repositum.tuwien.at/robots.txt

INTERESTING_INFO = [
    'dc.contributor.advisor',
    'dc.contributor.author',
    'dc.date.accessioned',
    'dc.date.issued',
    'dc.date.submitted',
    'dc.identifier.uri',
    'dc.language.iso',
    'dc.subject',
    'cd.title',
    'dc.type',
    'cd.contributor.assistant',
    'tux.publication.orgunit',
    'cd.type.qualificationlevel',
    'dc.identifier.libraryid',
    'dc.description.numberOfPages',
    'dc.thesistype',
    'item.openairetype',
    'item.openaccessfulltext',
    'crisitem.author.dept',
    'crisitem.author.parentorg'
]

def next_results_page(soup: BeautifulSoup) -> str or None:
    """
    Get the link to the next page of search results
    :param soup: created from a search page in /simple-search
    :return: the URL to the next page of search results or None if there is no next page
    """
    # Find the pagination list
    pagination_list = soup.find('ul', class_='pagination pull-right')
    if not pagination_list:
        return None
    # Find the link called "Next"
    next_link = pagination_list.find('a', string="Next")
    if next_link:
        return next_link['href']
    else:
        return None

def get_theses_links(soup: BeautifulSoup) -> list[str]:
    """
    On a search page, get all the links to the theses
    :param soup: created from a search results page in /simple-search
    :return:
    """
    theses_table = soup.find('table', class_='table table-hover')
    # find all links in theses_table that start with /handle/
    links = []
    if theses_table:
        for a in theses_table.find_all('a', href=True):
            if a['href'].startswith('/handle/'):
                links.append(a['href'])
    return links

def get_all_theses_links(start_page: str) -> list[str]:
    """
    Iterates through all pages of search results to get all the links to the theses
    :param start_page: the URL of the first page of search results
    :return: a list of URLs to the theses
    """
    all_links = []
    current_page = requests.get(start_page)
    while True:
        soup = BeautifulSoup(current_page.content, 'html.parser')
        all_links.extend(get_theses_links(soup))
        print(f'\r{len(all_links)} thesis links found', end='')
        next_page = next_results_page(soup)
        if next_page:
            time.sleep(CRAWL_DELAY)  # wait 1 second to avoid overload
            current_page = requests.get(next_page)
        else:
            break
    return all_links

def save_links(links: list[str]):
    """
    Save a list of links to a txt file
    :param links: list of URLs
    :return:
    """
    with open('thesis_links.txt', 'w') as f:
        for link in links:
            f.write(link + '\n')

def get_thesis_info(link: str) -> dict:
    """
    Get the metadata of a thesis from the full item record
    :param link: URL of the thesis page
    :return: dictionary of properties
    """
    info_dict = {}
    thesis_page = requests.get(DOMAIN + link)
    soup = BeautifulSoup(thesis_page.content, 'html.parser')
    button = soup.find('a', class_ = 'btn btn-primary')
    print(f'button string: {button.text}')
    if not button:
        raise ValueError("No full item record found")
    full_record = requests.get(DOMAIN + button['href'])
    soup = BeautifulSoup(full_record.content, 'html.parser')

    # Get the (interesting) rows from the page
    table = soup.find('div', id='wrapperDisplayItem')
    rows = table.find_all('div', class_="row metadata-row")
    for row in rows:
        if row.find('div', class_="col-md-3 col-sm-4 metadataFieldLabel"):
            info = row.find('div', class_="col-md-3 col-sm-4 metadataFieldLabel").text.strip()
            data = row.find('div', class_="col-md-8 col-sm-8 metadataFieldValue").text.strip()
            if info in INTERESTING_INFO:
                if info in info_dict.keys():
                    info_dict[info] = info_dict[info] + ', ' + data
                else:
                    info_dict[info] = data

    return info_dict

def get_thesis_pdf(link: str) -> bytes:
    """
    Find the link to the PDF of the thesis and download it
    :param link: URL of the thesis page
    :return:
    """
    thesis_page = requests.get(DOMAIN + link)
    soup = BeautifulSoup(thesis_page.content, 'html.parser')
    link_div = soup.find('div', class_='item-bitstream-grid-bitstream-type')
    pdf_link = link_div.find('a')['href']
    pdf = requests.get(DOMAIN + pdf_link).content
    return pdf

def parse_pdf(pdf: bytes) -> str:
    """
    Extract text from the first page of a PDF
    :param pdf: the pdf file in bytes
    :return: all text on the first page
    """
    if pdf:
        reader = PdfReader(BytesIO(pdf))
        first_page = reader.pages[0].extract_text()
        return first_page
    else:
        return ""

def get_degree(raw_text: str) -> str or None:
    """
    Extract the name of the degree for which a thesis was completed
    :param raw_text: the text on the first page of the thesis PDF
    :return: name of the degree (without whitespaces) or None if not found
    """
    opening_text_en = "degreeof"  # the text (without spaces) which directly precedes the degree
    closing_text_en = "by"  # the text (without spaces) which directly follows the degree
    opening_text_de = "desStudiums"  # the text (without spaces) which directly precedes the degree
    closing_text_de = "eingereichtvon"  # the text (without spaces) which directly follows the degree
    # remove all whitespaces from the text (because of faulty pdf decoding which adds whitespaces)
    text = ''.join(raw_text.split())
    # English
    if opening_text_en in text:
        start = text.find(opening_text_en) + len(opening_text_en)
        end = text.find(closing_text_en)
        degree = text[start:end]
    # Deutsch
    elif opening_text_de in text:
        start = text.find(opening_text_de) + len(opening_text_de)
        end = text.find(closing_text_de)
        degree = text[start:end]
    else:
        degree = None
    return degree

def scrape_publication_page(id: int,
                            path: str = '/handle',
                            doi_prefix: str = '/20.500.12708/') -> dict or str:
    """
    Get all metadata from a publication page (thesis or other resource)
    :param id: the id of the publication (the number at the end of the URL, after the last slash)
    :param path: the beginning of the path to the publication page
    :param doi_prefix: the prefix of the DOI
    :return: dictionary of metadata or error message
    """
    if not isinstance(id, int):
        raise ValueError('id must be an integer')
    if id < 0:
        raise ValueError('id must be a positive integer')
    if id >= 300_000:
        raise ValueError('id must be less than 300_000')
    link = DOMAIN + path + doi_prefix + str(id) + '?mode=full'
    time.sleep(CRAWL_DELAY)  # to be sure to respect the robots.txt
    page = requests.get(link)
    if page.status_code != 200:
        return f'Negative response: {page.status_code}'

    soup = BeautifulSoup(page.content, 'html.parser')

    # Check if the identifier exists
    if soup.find(lambda tag: tag.name=='h1' and tag.get_text().strip == 'Invalid Identifier'):
        return 'Invalid Identifier'

    # Find table with metadata
    wrapper_display = soup.find('div', id='wrapperDisplayItem')
    if not wrapper_display:
        return 'No wrapperDisplayItem found'
    table = wrapper_display.find('div', class_='row')
    if not table:
        return 'No row class found'
    rows = table.find_all('div', class_='row metadata-row')
    if not rows:
        return 'No metadata rows found'
    else:
        attributes =  get_resource_attributes(rows)

    # Find metrics
    views, downloads = get_metrics(soup)
    attributes['Views'] = views
    attributes['Downloads'] = downloads

    # Find PDF link
    attributes['PDF link'] = get_pdf_link(wrapper_display)

    return attributes

def get_resource_attributes(rows: list) -> dict:
    """
    Extract all metadata from the rows of a publication page
    :param rows: list of bs4 Tag objects obtained in scrape_publication_page()
    :return: dictionary of metadata
    """
    attributes = {}
    for row in rows:
        label = row.find('div', class_='col-md-3 col-sm-4 metadataFieldLabel')
        value = row.find('div', class_='col-md-8 col-sm-8 metadataFieldValue')
        # add language field here if desired, but it's usually not very informative
        if label and value:
            # Sometimes random whitespaces are added to the text, so we strip it
            label = label.text.strip()
            value = value.text.strip()
            if label in attributes.keys():  # check if the label is already in the dictionary
                attributes[label] = attributes[label] + ', ' + value  # extend the list
            else:
                attributes[label] = value
    return attributes

def get_metrics(soup: BeautifulSoup) -> tuple[str, str]:
    """
    Get the number of views and downloads of a publication
    :param soup: created from a publication page
    :return: number of views and downloads
    """
    panel = soup.find('div', class_='panel-list-right')
    if not panel:
        views = downloads = "Panel not found"
    # Get number of views
    view_counter = panel.find('span', id='metric-counter-view')
    if view_counter:
        views = view_counter.text.strip()
    else:
        views = "Views not found"
    # Get number of downloads
    download_counter = panel.find('span', id='metric-counter-download')
    if download_counter:
        downloads = download_counter.text.strip()
    else:
        downloads = "Downloads not found"
    return views, downloads

def get_pdf_link(wrapper_display: Tag) -> str:
    """
    Extract the link to the PDF of a publication from the wrapperDisplayItem in the page
    :param wrapper_display: a bs4 Tag object obtained in scrape_publication_page()
    :return: URL of the PDF
    """
    link_div = wrapper_display.find('div', class_='item-bitstream-grid-bitstream-type')
    if not link_div:
        return "No bitstream grid found"
    pdf_link = link_div.find('a')['href']
    return pdf_link

def collect_metadata(ids: list[int]):
    """
    Iterate through a list of ids and save the metadata of each publication to a json file
    :param ids: list of ids (the number at the end of the URL, after the last slash)
    :return:
    """
    for id in ids:
        with open(f'metadata/{id}.json', 'w') as file:
            json.dump(scrape_publication_page(id), file, indent=4)

if __name__ == '__main__':
    # test: try the first 100 pages
    collect_metadata(list(range(1, 100)))


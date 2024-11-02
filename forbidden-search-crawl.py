""""
date: 2024-11-02
author: Emile Johnston

Scraping https://repositum.tuwien.at/simple-search is not allowed.
DON'T RUN THIS CODE unless the rules have changed.
rules: https://repositum.tuwien.at/robots.txt

This script is for making a list of all theses published at TU Wien between 2020 and 2024
(around 7000 theses)
"""

from scraping import *

"""
all_links = get_all_theses_links(MAIN_PAGE)
save_links(all_links)

# get info for the first thesis
info = get_thesis_info(all_links[0])
print(info)

# get pdf for the first thesis
pdf = get_thesis_pdf(all_links[0])

# parse pdf
text = parse_pdf(pdf)
print(text)

# get degree
degree = get_degree(text)
print(degree)
"""
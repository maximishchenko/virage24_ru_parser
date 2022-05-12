from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
import requests
import csv

# todo перенести названия css-селекторов в константы классов
# logging


class Url:
    """ Base operations with URLs
    """

    def get_base_url(self, url) -> str:
        """ Return base-url substring

        Args:
            url (string): full url string

        Returns:
            string: base url substring
        """
        scheme = urlparse(url).scheme
        netloc = urlparse(url).netloc
        base_url = urlunparse((scheme, netloc, '', None, '', ''))
        return base_url

    
    def make_url(self, url, path, params=None, anchors=None):
        """ create url from arguments

        Args:
            url (string): url-path

        Returns:
            string: full url string with path, paramenters, anchors if exists
        """
        url_parse = urlparse(url)
        scheme = url_parse.scheme
        netloc = url_parse.netloc
        url_path = url_parse.path
        if url_path:
            path = url_path
        url = urlunparse((scheme, netloc, path, '', params, anchors))
        return url


class Parser(Url):
    """ wirage24.ru website catalog parser
    """

    """ Category list CSS-selector in DOM """
    category_css_selector = ".catalog_section_list .section_item li.sect a"

    """ Product item CSS-selector in DOM
    """
    product_item_css_selector = ".catalog_block .catalog_item:not(.big)>div .item_info"

    """ Pagination block CSS-selector in DOM
    """
    pagination_block_css_selector = ".module-pagination .nums a"

    """ Pagination URL-parameter string
    """
    pagination_url_parameter = "PAGEN_1"


    def __init__(self, catalog_url_link) -> None:
        self.url = catalog_url_link
        self.base_url = self.get_base_url(self.url)


    def get_categories_dict(self) -> dict:
        url_link_content = requests.get(self.url)
        catalog = BeautifulSoup(url_link_content.text, 'lxml')
        catalog_sections = catalog.select(self.category_css_selector)
        catalog_sections_dict = {}
        for link in catalog_sections:
            catalog_link = self.make_url(self.base_url, link['href'])
            catalog_sections_dict[link.text] = catalog_link
        try:
            len(catalog_sections_dict) > 0
            return catalog_sections_dict
        except Exception as e:
            print(e)
            pass


    def get_url_pagination_size(self, url) -> int:
        url_link_content = requests.get(url)
        paginator = BeautifulSoup(url_link_content.text, 'lxml')
        paginator_items = paginator.select(self.pagination_block_css_selector)
        if not paginator_items:
            last_pager = 1
        else:
            last_pager_element = paginator_items[-1].text
            last_pager = int(last_pager_element)
        return last_pager

    
    def get_product_url_with_pagination(self, url, page) -> str:
        pager = '{}={}'.format(self.pagination_url_parameter, page)
        product_url = self.make_url(url, '/', pager)
        return product_url


    def get_product_data(self, url) -> list:
        product_html_content = requests.get(url)
        products = BeautifulSoup(product_html_content.text, 'lxml')
        product_items = products.select(self.product_item_css_selector)
        products_list = []
        for i in product_items:
            """ Get price value """
            price_html = i.find("span", attrs = {'class': 'price_value'})
            if price_html is not None:
                price_text = price_html.get_text()
                price_string = price_text.replace(" ", "")
                price_string = price_text.replace(",", ".")
            else:
                price_string = 0
            price = price_string
            """ Get product name value """
            product_name_html = i.find("a", attrs = {"class": "dark_link js-notice-block__title option-font-bold font_sm"})
            product_name_text = product_name_html.get_text()
            """ Get product code value """
            product_code_html = i.find("div", attrs = {"class": "muted font_sxs"})
            product_code_text = product_code_html.get_text()
            product_code = product_code_text.replace("Код: ", "")
            """ Get price currency value """
            price_currency_html = i.find("span", attrs = {'class': 'price_currency'})
            if price_currency_html is not None:
                price_currency_text = price_currency_html.get_text()
                price_currency = price_currency_text.replace(" ", "")
            else:
                price_currency = ""
            """ Get product unit value """
            product_unit_html = i.find("span", attrs = {'class': 'price_measure'})
            if product_unit_html is not None:
                product_unit_text = product_unit_html.get_text()
                product_unit = product_unit_text.replace("/", "")
            else:
                product_unit = ""
            product_url = i.find("a", attrs = {'class': 'dark_link js-notice-block__title option-font-bold font_sm'})
            product_url_link = self.make_url(self.base_url, product_url["href"])
            product = (product_name_text, product_code, price, price_currency, \
                product_unit, product_url_link)
            products_list.append(product)
        return products_list


class Import:

    """ CSV file for import data """
    csv_file = 'import.csv'

    """ Name header """
    name = "Наименование"

    """ Product code header """
    code = "Код товара"

    """ Price header """
    price = "Цена"

    """ Currency header """
    currency = "Валюта"

    """ Unit header """
    unit = "Единица измерения"

    """ URL header """
    url = "Ссылка на товар в каталоге"

    """ Category header """
    category = "Категория"

    def get_columns(self) -> list:
        """ Generate columns headers list for dataframe

        Returns:
            list: Columns list
        """
        columns = [self.name, self.code, self.price, self.currency, self.unit,\
            self.url, self.category]
        return columns


if __name__ == "__main__":
    catalog_url = "https://www.virage24.ru/shop/"
    parser = Parser(catalog_url)
    data = Import()
    products = []
    """ Get catalog categories
    """
    categories = parser.get_categories_dict()
    
    with open(data.csv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(data.get_columns())
        for category, url in categories.items():
            pagination_size = parser.get_url_pagination_size(url)
            for page in range(1, pagination_size + 1):
                product_page_url = parser.get_product_url_with_pagination(url, \
                    page)
                products_in_page = parser.get_product_data(product_page_url)
                for single_product in products_in_page:
                    single_product = single_product + (category,)
                    print(single_product)
                    writer.writerow(single_product)
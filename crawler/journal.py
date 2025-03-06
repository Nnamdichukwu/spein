# -*- coding: utf-8 -*-
import scrapy
import logging
import os

from urllib.parse import urljoin
from core.connection import Connection as conn

class JournalsSpider(scrapy.Spider):
    name = 'journals'
    allowed_domains = ['frontierspartnerships.org']
    start_urls = ['https://www.frontierspartnerships.org/journals']
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'DOWNLOAD_DELAY': 0.5,
        'COOKIES_ENABLED': True,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429, 403],
        'REDIRECT_ENABLED': True,
        'REDIRECT_MAX_TIMES': 5,
        'DOWNLOAD_TIMEOUT': 30,
        'HTTPERROR_ALLOWED_CODES': [404, 405, 400],
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
    }

    def __init__(self, *args, **kwargs):
        super(JournalsSpider, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.INFO)
        
        # Handle start_urls parameter
        if 'start_urls' in kwargs:
            if isinstance(kwargs['start_urls'], str):
                self.start_urls = [kwargs['start_urls']]
            else:
                self.start_urls = kwargs['start_urls']

        # Initialize database and pdfs directory
        db = conn()
        db.create_table_if_not_exists("files")
        db.close()
        


    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                headers={
                    'Referer': 'https://www.frontierspartnerships.org/journals/'
                },
                meta={
                    'dont_redirect': False,
                    'handle_httpstatus_list': [301, 302]
                },
                dont_filter=True
            )

    def parse(self, response):
        # If this is an article page, parse it directly
        if '/articles/' in response.url and '/full' in response.url:
            return self.parse_article(response)
        
        journal_links = response.css('a[href*="/journals/"]::attr(href)').getall()
        
        for link in journal_links:
            if '/articles/' in link:
                yield scrapy.Request(
                    url=response.urljoin(link),
                    callback=self.parse_article,
                    errback=self.handle_error,
                    dont_filter=True
                )
            else:
                yield scrapy.Request(
                    url=response.urljoin(link),
                    callback=self.parse_journal,
                    errback=self.handle_error
                )

    def parse_journal(self, response):
        # If this is an article page, parse it directly
        if '/articles/' in response.url and '/full' in response.url:
            return self.parse_article(response)
            
        article_links = response.css('a[href*="/articles/"]::attr(href)').getall()
        
        for link in article_links:
            if link and '/full' in link:
                yield scrapy.Request(
                    url=response.urljoin(link),
                    callback=self.parse_article,
                    errback=self.handle_error,
                    dont_filter=True 
                )

    def parse_article(self, response):
        self.logger.info(f"Parsing article page: {response.url}")
        
        # First try direct PDF link
        pdf_links = response.css('a[href*="/pdf"]::attr(href)').getall()
        if not pdf_links:
            # Try finding download button
            pdf_links = response.css('a.download-button::attr(href)').getall()
            if not pdf_links:
                # Try finding any link that might be a PDF
                pdf_links = [link for link in response.css('a::attr(href)').getall() if '/pdf' in link.lower()]
        
        # If we still don't have PDF links, try constructing one from the article URL
        if not pdf_links:
            article_url = response.url
            if '/full' in article_url:
                pdf_url = article_url.replace('/full', '/pdf')
                pdf_links = [pdf_url]
        
        self.logger.info(f"Found {len(pdf_links)} potential PDF links on {response.url}")
        
        for link in pdf_links:
            full_url = response.urljoin(link)
            self.logger.info(f"Attempting to download PDF from: {full_url}")
            yield scrapy.Request(
                url=full_url,
                callback=self.save_pdf,
                errback=self.handle_error,
                meta={'source_url': response.url, 'dont_redirect': True},
                dont_filter=True  
            )

    def save_pdf(self, response):
        self.logger.info(f"Processing response from {response.url}")
        self.logger.info(f"Response headers: {response.headers}")
        self.logger.info(f"Content type: {response.headers.get('Content-Type', b'').decode()}")
        
        db = conn()
        if not response.headers.get('Content-Type', b'').startswith(b'application/pdf'):
            self.logger.warning(f"Skipping non-PDF response from {response.url} (Content-Type: {response.headers.get('Content-Type', b'').decode()})")
            return

        filename = response.headers.get('Content-Disposition', b'').decode()
        if not filename:
            filename = response.url.split('/')[-1]
            if not filename.endswith('.pdf'):
                filename += '.pdf'

        # Check if file already exists
        if db.is_file_in_db(filename, "files"):
            self.logger.info(f"File {filename} already exists in database, skipping")
            return

        try:
            with open(f'pdfs/{filename}', 'wb') as f:
                f.write(response.body)
            db.save_to_db(filename, "files", response.meta.get('source_url'))
            self.logger.info(f"Successfully saved {filename} to database and file system")
        except Exception as e:
            self.logger.error(f"Error saving {filename}: {str(e)}")
            raise e
        finally:
            db.close()

    def handle_error(self, failure):
        logging.error(f"Request failed: {failure.request.url}")
        logging.error(str(failure.value))

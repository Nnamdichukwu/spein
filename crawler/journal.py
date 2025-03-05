# -*- coding: utf-8 -*-
import scrapy
import logging

from urllib.parse import urljoin
from core.connection import Connection as conn

class JournalsSpider(scrapy.Spider):
    name = 'journals'
    allowed_domains = ['frontierspartnerships.org']
    start_urls = ['https://www.frontierspartnerships.org/journals']
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 32,
        'DOWNLOAD_DELAY': 0.5,
        'COOKIES_ENABLED': False,
    }

    def __init__(self, *args, **kwargs):
        super(JournalsSpider, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.INFO)
        
        # Initialize database
        db = conn()
        db.create_table_if_not_exists("files")
        db.close()

    def parse(self, response):
        
        journal_links = response.css('a[href*="/journals/"]::attr(href)').getall()
        
        for link in journal_links:
            if '/articles/' in link:
                yield scrapy.Request(
                    url=response.urljoin(link),
                    callback=self.parse_article,
                    errback=self.handle_error
                )
            else:
                yield scrapy.Request(
                    url=response.urljoin(link),
                    callback=self.parse_journal,
                    errback=self.handle_error
                )

    def parse_journal(self, response):
        
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
        
        pdf_links = response.css('a[href*="/pdf"]::attr(href)').getall()
        
        for link in pdf_links:
            full_url = response.urljoin(link)
            yield scrapy.Request(
                url=full_url,
                callback=self.save_pdf,
                errback=self.handle_error,
                meta={'source_url': response.url},
                dont_filter=True  
            )

    def save_pdf(self, response):
        db = conn()
        if not response.headers.get('Content-Type', b'').startswith(b'application/pdf'):
            logging.warning(f"Skipping non-PDF response from {response.url} (Content-Type: {response.headers.get('Content-Type', b'').decode()})")
            return

        filename = response.headers.get('Content-Disposition', b'').decode()
        if not filename:
            filename = response.url.split('/')[-1]
            if not filename.endswith('.pdf'):
                filename += '.pdf'

        # Check if file already exists
        if db.is_file_in_db(filename, "files"):
            logging.info(f"File {filename} already exists in database, skipping")
            return

        try:
            
            db.save_to_db(filename, "files", response.meta.get('source_url'))
            logging.info(f"Successfully saved {filename} to database")
        except Exception as e:
            logging.error(f"Error saving {filename} to database: {str(e)}")
            raise e
        finally:
            db.close()

    def handle_error(self, failure):
        logging.error(f"Request failed: {failure.request.url}")
        logging.error(str(failure.value))

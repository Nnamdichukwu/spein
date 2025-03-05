import scrapy
import logging
from urllib.parse import urljoin
from core.connection import Connection as conn

class JournalsSpider(scrapy.Spider):
    name = 'journals'
    allowed_domains = ['frontierspartnerships.org']
    start_urls = ['https://www.frontierspartnerships.org/journals']
    
    def __init__(self, *args, **kwargs):
        super(JournalsSpider, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.INFO)
        
        # Initialize database
        db = conn()
        db.create_table_if_not_exists("files")
        db.close()

    def parse(self, response):
        # Find all links on the page
        for link in response.css('a::attr(href)').getall():
            absolute_url = urljoin(response.url, link)
            
            # Only follow links within our domain
            if any(domain in absolute_url for domain in self.allowed_domains):
                yield scrapy.Request(absolute_url, callback=self.parse_page)

    def parse_page(self, response):
        # Only parse HTML pages
        content_type = response.headers.get('Content-Type', b'').decode('utf-8', 'ignore')
        if not content_type.startswith('text/html'):
            return

        pdf_links = []
        
      
        pdf_links.extend(
            (link, text.strip()) for link, text in 
            zip(response.css('a::attr(href)').getall(), response.css('a::text').getall())
            if 'pdf' in text.lower()
        )
        

        pdf_links.extend(
            (link, link.split('/')[-1]) for link in response.css('a::attr(href)').getall()
            if link.lower().endswith('.pdf')
        )
        
   
        pdf_links.extend(
            (link, text.strip()) for link, text in 
            zip(response.css('a[class*="download"]::attr(href)').getall(), 
                response.css('a[class*="download"]::text').getall())
        )
        
        seen = set()
        unique_pdf_links = [(link, name) for link, name in pdf_links 
                          if not (link in seen or seen.add(link))]
        
        if unique_pdf_links:
            self.logger.info(f"Found {len(unique_pdf_links)} potential PDF links on {response.url}")
            
            for pdf_link, pdf_name in unique_pdf_links:
                absolute_url = urljoin(response.url, pdf_link)
                
                # Create a filename from the URL if name is empty
                if not pdf_name or len(pdf_name.strip()) == 0:
                    pdf_name = absolute_url.split('/')[-1]
                
                # Ensure filename ends with .pdf
                if not pdf_name.lower().endswith('.pdf'):
                    pdf_name += '.pdf'
                
                # Download the PDF
                yield scrapy.Request(
                    absolute_url,
                    callback=self.download_pdf,
                    meta={
                        'filename': pdf_name,
                        'source_url': response.url,
                        'dont_filter': True,
                        'handle_httpstatus_list': [404, 403, 500]
                    }
                )
        
        # Continue crawling
        for link in response.css('a::attr(href)').getall():
            absolute_url = urljoin(response.url, link)
            if any(domain in absolute_url for domain in self.allowed_domains):
                yield scrapy.Request(absolute_url, callback=self.parse_page)

    def download_pdf(self, response):
        try:
            # Log the response headers to debug content type issues
            self.logger.info(f"Response headers for {response.url}: {response.headers}")
            
            content_type = response.headers.get('Content-Type', b'').decode('utf-8', 'ignore')
            self.logger.info(f"Content type for {response.url}: {content_type}")

            # Check if the response is a PDF
            if not content_type.startswith('application/pdf'):
                self.logger.warning(f"Skipping non-PDF response from {response.url} (Content-Type: {content_type})")
                return

            filename = response.meta.get('filename', response.url.split("/")[-1])
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            
            source_url = response.meta.get('source_url')
            file_data = response.body
            
            # Create new connection for saving
            db = conn()
            cur = db.get_connection().cursor()
            cur.execute("""
                INSERT INTO files (filename, source_url, file_data) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (filename) DO NOTHING
            """, (filename, source_url, file_data))
            db.get_connection().commit()
            db.close()
            
            self.logger.info(f"Saved {filename} to database (from {source_url})")

        except Exception as e:
            self.logger.error(f"Error downloading PDF {response.url}: {str(e)}")

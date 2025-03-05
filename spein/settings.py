BOT_NAME = "spein"

SPIDER_MODULES = ["crawler"]
NEWSPIDER_MODULE = "crawler"


ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 16


DOWNLOAD_DELAY = 1

DOWNLOADER_MIDDLEWARES = {
   "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
   "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
}

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.selectreactor.SelectReactor"
FEED_EXPORT_ENCODING = "utf-8"

class NewsFormatter:
    @staticmethod
    def _print_header():
        print("\n" + "="*80)

    @staticmethod
    def _print_footer():
        print("="*80 + "\n")

    @classmethod
    def print_unified(cls, news):
        cls._print_header()
        print(f"ID: {news.id}")
        print(f"Title: {news.title}")
        print(f"Authors: {', '.join(news.authors)}")
        print(f"Created: {news.created}")
        print(f"Updated: {news.updated}")
        print(f"URL: {news.url}")
        print(f"\nStocks: {', '.join(news.symbols)}")
        print(f"Channels: {', '.join(news.channels)}")
        print(f"Tags: {', '.join(news.tags)}")
        print(f"\nTeaser: {news.teaser}")
        print(f"\nBody: {news.body}")
        cls._print_footer()

    @classmethod
    def print_rest_api(cls, news):
        cls._print_header()
        print(f"ID: {news.id}")
        print(f"Title: {news.title}")
        print(f"Author: {news.author}")
        print(f"Created: {news.created}")
        print(f"Updated: {news.updated}")
        print(f"URL: {news.url}")
        print("\nStocks:")
        for stock in news.stocks:
            print(f" - {stock.name}")
        print("\nChannels:")
        for channel in news.channels:
            print(f" - {channel.name}")
        print("\nTags:")
        for tag in news.tags:
            print(f" - {tag.name}")
        print(f"\nTeaser: {news.teaser}")
        print(f"\nBody: {news.body}")
        if news.image:
            print("\nImages:")
            for img in news.image:
                print(f" - Size: {img.size}")
                print(f" URL: {img.url}")
        cls._print_footer()

    @classmethod
    def print_websocket(cls, news):
        cls._print_header()
        print(f"API Version: {news.api_version}")
        print(f"Kind: {news.kind}")
        print(f"\nData:")
        print(f"Action: {news.data.action}")
        print(f"ID: {news.data.id}")
        print(f"Timestamp: {news.data.timestamp}")
        print(f"\nContent:")
        content = news.data.content
        print(f"ID: {content.id}")
        print(f"Title: {content.title}")
        print(f"Authors: {', '.join(content.authors)}")
        print(f"Created: {content.created_at}")
        print(f"Updated: {content.updated_at}")
        print(f"URL: {content.url}")
        print("\nSecurities:")
        for sec in content.securities:
            print(f" - Symbol: {sec.symbol}")
            print(f" Exchange: {sec.exchange}")
            print(f" Primary: {sec.primary}")
        print(f"\nChannels: {', '.join(content.channels)}")
        print(f"Tags: {', '.join(content.tags) if content.tags else ''}")
        print(f"\nTeaser: {content.teaser}")
        print(f"\nBody: {content.body}")
        if content.image:
            print("\nImages:")
            for img in content.image:
                print(f" - Size: {img.size}")
                print(f" URL: {img.url}")
        cls._print_footer()
    





    def process_news_for_storage(self):
    
        # STEP 1: Text cleanup, HTML parsing, character removal
        def clean_content(content):
            if pd.isna(content) or not isinstance(content, str):
                return content  # return as-is if it's NaN or not a string

            # Skip content that looks like a filename or URL
            if content.startswith(('http://', 'https://', '/')):
                return content    

            cleaned_text = BeautifulSoup(content, 'html.parser').get_text(' ')
            cleaned_text = cleaned_text.replace('\xa0', ' ')
            cleaned_text = re.sub(r'\s+([.,;?!])', r'\1', cleaned_text)
            cleaned_text = re.sub(r'([.,;?!])\s+', r'\1 ', cleaned_text)
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Remove extra spaces
            return cleaned_text.strip()

        # Cleaning textual columns
        self.news_dfs['Current'][['contents', 'teaser', 'title']] = self.news_dfs['Current'][['contents', 'teaser', 'title']].applymap(clean_content)    
        # Reset Index inorder for below operations to work
        self.news_dfs['Current'].reset_index(inplace=True) # Reset multiindex to apply the mapping
        self.news_dfs['Current'] = self.news_dfs['Current'].sort_values('time')

        # STEP 2: Convert to Eastern Time Zone
        def convert_to_eastern(series):
            return pd.to_datetime(series, utc=True).dt.tz_convert('US/Eastern') # utc=True interprets the original series as UTC time.
     
        date_columns = ['time', 'createdat', 'updatedat']
        for col in date_columns:
            self.news_dfs['Current'][col] = convert_to_eastern(self.news_dfs['Current'][col])

        # STEP 3: Modify & map NewSourceSymbol (Tiingo or Benzinga) to a format which can then be easily stored
        def map_index_symbol(symbol): # Map the symbol directly
            return self.news_symbols_map.get(symbol, symbol)
        # self.news_dfs['Current']['symbols'] = self.news_dfs['Current']['symbols'].apply(lambda x: [getattr(item, 'Value') if hasattr(item, 'Value') else item for item in x]) # Process symbols column
        self.news_dfs['Current']['symbols'] = self.news_dfs['Current']['symbols'].apply(lambda x: [map_index_symbol(item) for item in x])
        self.news_dfs['Current']['symbol'] = self.news_dfs['Current']['symbol'].map(map_index_symbol) # Reset the index for symbol column to apply the mapping
        self.news_dfs['Current'].set_index(['symbol', 'time'], inplace=True) # Set the index back - Note time is same as updatedat or crawldate

        # STEP 4: Remove groups with NO data
        def filter_groups_with_data(group): return len(group) > 0
        self.news_dfs['Current'] = self.news_dfs['Current'].groupby(level='symbol').filter(filter_groups_with_data)
            
        # STEP 5: Remove unused levels from the index
        self.news_dfs['Current'].index = self.news_dfs['Current'].index.remove_unused_levels()


# Mapping of TIINGO column names to Benzinga column names
    def convert_tiingo_columns(self):
        if self.news_source.__name__ == 'TiingoNews':
            column_mapping = {
                'symbol': 'symbol',
                'time': 'time',
                'articleid': 'id',
                'url': 'author',
                'publisheddate': 'createdat',
                'crawldate': 'updatedat',
                'title': 'title',
                'description': 'contents',
                'source': 'categories',
                'tags': 'tags',
                'symbols': 'symbols'
            }

            self.news_dfs['Current'].rename(columns=column_mapping, inplace=True)
            self.news_dfs['Current']['id'] = self.news_dfs['Current']['id'].astype(int)
            self.news_dfs['Current']['categories'] = self.news_dfs['Current']['categories'].apply(lambda x: [x] if isinstance(x, str) else x)
            self.news_dfs['Current']['datasourceid'] = None
            self.news_dfs['Current']['teaser'] = None
        else:
            print("No need to convert columns for this news source.")


    def remove_news_with_no_content(self):
        total_articles = len(self.news_dfs['Current'])
        
        # Identify articles with content (non-empty, non-None, and non-NaN)
        articles_with_content_df = self.news_dfs['Current'][
            self.news_dfs['Current']['contents'].ne('') & ~pd.isna(self.news_dfs['Current']['contents'])]


        articles_with_content = len(articles_with_content_df)
        articles_missing_content = total_articles - articles_with_content

        print(f"Total articles fetched: {total_articles}")
        print(f"Articles with content: {articles_with_content}")
        print(f"Articles missing content: {articles_missing_content}")

        # Remove articles with missing content
        if self.remove_missing_content:
            self.news_dfs['Current'] = articles_with_content_df
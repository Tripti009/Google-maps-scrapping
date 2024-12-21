from playwright.sync_api import sync_playwright
import pandas as pd
import time
import re

class GoogleMapsScraper:
    def __init__(self):
        self.data = {
            'School Name': [], 'Website': [], 'Phone Number': [],
            'Address': [], 'Review Count': [], 'Average Rating': [],
            'Type of School': [], 'Hours of Operation': [], 'Current Status': []
        }
    
    def extract_text(self, page, xpath: str, field_name: str) -> str:
        """Safely extract text from an element if it exists."""
        try:
            element = page.locator(xpath)
            if element.count() > 0:
                text = element.inner_text()
                print(f"Found {field_name}: {text}")
                return text
            else:
                print(f"No element found for {field_name}")
                return None
        except Exception as e:
            print(f"Error extracting {field_name}: {e}")
            return None

    def extract_name(self, page) -> str:
        """Extract the school name."""
        try:
            name = page.locator('//h1[@class="DUwDvf lfPIob"]').inner_text()
            return name
        except Exception as e:
            print(f"Error extracting school name: {e}")
            return None

    def parse_hours(self, hours_text: str) -> tuple:
        """Parse hours text into status and hours."""
        if not hours_text:
            return None, None
        
        status = None
        hours = None
        
        if '⋅' in hours_text:
            parts = hours_text.split('⋅')
            status = parts[0].strip()
            hours = parts[1].strip() if len(parts) > 1 else None
        else:
            hours = hours_text.strip()
            
        return status, hours

    def scrape_listing(self, page, listing, index: int) -> None:
        """Scrape data from a single listing."""
        try:
            print(f"\nScraping school listing {index + 1}")
            
            listing.click()
            time.sleep(2)
            
            # Wait for main element and extract data
            page.wait_for_selector('//div[@class="TIHn2 "]', timeout=10000)
            
            school_name = self.extract_name(page)
            website = self.extract_text(page, '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]', 'Website')
            phone = self.extract_text(page, '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]', 'Phone Number')
            address = self.extract_text(page, '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]', 'Address')
            
            # Reviews
            reviews_count = self.extract_text(page, '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span//span//span[@aria-label]', 'Review Count')
            average_rating = self.extract_text(page, '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span[@aria-hidden]', 'Average Rating')
            
            if reviews_count:
                reviews_count = int(re.sub(r'[^\d]', '', reviews_count))
            if average_rating:
                average_rating = float(average_rating.replace(' ', '').replace(',', '.'))

            # Hours of operation
            hours_text = self.extract_text(page, '//button[contains(@data-item-id, "oh")]//div[contains(@class, "fontBodyMedium")]', 'Hours of Operation')
            current_status, hours_of_operation = self.parse_hours(hours_text)
            
            # Type of school
            school_type = self.extract_text(page, '//div[@class="LBgpqf"]//button[@class="DkEaL "]', 'Type of School')

            # Append data to the corresponding fields
            self.data['School Name'].append(school_name)
            self.data['Website'].append(website)
            self.data['Phone Number'].append(phone)
            self.data['Address'].append(address)
            self.data['Review Count'].append(reviews_count)
            self.data['Average Rating'].append(average_rating)
            self.data['Type of School'].append(school_type)
            self.data['Hours of Operation'].append(hours_of_operation)
            self.data['Current Status'].append(current_status)

        except Exception as e:
            print(f"Error scraping school listing: {e}")
            for key in self.data:
                self.data[key].append(None)

    def scrape(self, search_term: str, total: int) -> pd.DataFrame:
        """Main scraping function."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            print(f"Searching for: {search_term}")
            page.goto("https://www.google.com/maps", timeout=60000)
            page.fill('//input[@id="searchboxinput"]', search_term)
            page.keyboard.press("Enter")
            
            print("Waiting for results...")
            page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=30000)
            time.sleep(3)
            
            print("Scrolling for more results...")
            previously_counted = 0
            scroll_attempts = 0
            
            while scroll_attempts < 10:
                page.mouse.wheel(0, 10000)
                time.sleep(2)
                
                current_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                print(f"Found {current_count} listings...")
                
                if current_count >= total or current_count == previously_counted:
                    listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
                    print(f"Final count: {len(listings)} listings")
                    break
                
                previously_counted = current_count
                scroll_attempts += 1
            
            for i, listing in enumerate(listings):
                self.scrape_listing(page, listing.locator("xpath=.."), i)
            
            browser.close()
            
            df = pd.DataFrame(self.data)
            df = df.dropna(axis=1, how='all')
            return df

def main():
    search_term = "schools in Rajesthan"
    total_listings = 10  # Adjust this number based on your requirements
    
    scraper = GoogleMapsScraper()
    df = scraper.scrape(search_term, total_listings)
    
    df = df.fillna('')
    df.to_csv('schools_detailed.csv', index=False)
    simple_columns = ['School Name', 'Address', 'Phone Number', 'Website', 'Type of School', 'Hours of Operation', 'Current Status']
    df_simple = df[simple_columns]
    df_simple.to_csv('schools_simple.csv', index=False)
    
    print("\nData Frame Head:")
    print(df.head())
    print("\nData Frame Shape:", df.shape)
    print("\nColumns found:", list(df.columns))

if __name__ == "__main__":
    main()

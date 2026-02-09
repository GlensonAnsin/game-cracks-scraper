from playwright.sync_api import sync_playwright
from sqlmodel import Field, Session, SQLModel, create_engine, select
from dotenv import load_dotenv
import time
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

class RepackGame(SQLModel, table=True):
    __tablename__ = "fitgirl_repacks"
    
    id: int = Field(default=None, primary_key=True)
    title: str
    link: str = Field(unique=True)
    
def create_db_tables():
    SQLModel.metadata.create_all(engine)
    
def save_batch_to_db(games_data: list):
    with Session(engine) as session:
        new_games_count = 0
        
        for game in games_data:
            statement = select(RepackGame).where(RepackGame.link == game["link"])
            existing_game = session.exec(statement).first()
            
            if not existing_game:
                new_db_entry = RepackGame(
                    title = game["title"],
                    link = game["link"]
                )
                session.add(new_db_entry)
                new_games_count += 1
        
        session.commit()
        print(f"Saved {new_games_count} new games to DB.")

def scrape_fitgirl_latest():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(0)

        print("Navigating to fitgirl-repacks...")
        fitgirl_home = "https://fitgirl-repacks.site/"
        page.goto(fitgirl_home)
        
        # --- EXTRACTION ---
        print("Page loaded. Extracting data...")
        
        game_items = page.query_selector_all('.wplp-box-item a')
        game_urls = []
        
        for el in game_items:
            url = el.get_attribute('href')
            if url: 
                game_urls.append(url)
        
        print(f"Found {len(game_urls)} total games.")
        
        current_batch_data = []
        
        for i, url in enumerate(game_urls):
            try:
                print(f"[{i+1}/{len(game_urls)}] Visiting: {url}")
                
                page.goto(url)
                
                title_el = page.wait_for_selector('h1.entry-title', timeout=5000)
                
                if title_el:
                    title = title_el.inner_text().strip()
                    current_batch_data.append({
                        "title": title,
                        "link": url
                    })
            
                time.sleep(1) 

            except Exception as e:
                print(f"Skipping {url}: {e}")
                continue
            
        # --- SAVING TO DB ---
        print(f"Successfully scraped {len(current_batch_data)} games.")
        if current_batch_data:
            save_batch_to_db(current_batch_data)

        browser.close()
        print("Browser closed.")

if __name__ == "__main__":
    print("Checking Database...")
    create_db_tables()
    
    print("Starting Scraper...")
    scrape_fitgirl_latest()
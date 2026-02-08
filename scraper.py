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

def scrape_fitgirl_az():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(0)

        print("Navigating to fitgirl-repacks...")
        page.goto("https://fitgirl-repacks.site/all-my-repacks-a-z/") 
        
        while True:
            # --- EXTRACTION ---
            print("Page loaded. Extracting data...")
            
            game_items = page.query_selector_all('ul.lcp_catlist li')
            
            print(f"Found {len(game_items)} total games.")
            
            current_batch_data = []
            
            for item in game_items:
                try:
                    link_el = item.query_selector('a')
                    if not link_el: continue
                    
                    title = link_el.inner_text().strip()
                    link = link_el.get_attribute('href')
                    
                    if not title or not link: continue

                    current_batch_data.append({
                        "title": title,
                        "link": link
                    })
                    
                except Exception:
                    continue

            # --- SAVING TO DB ---
            print(f"Successfully scraped {len(current_batch_data)} games.")
            if current_batch_data:
                save_batch_to_db(current_batch_data)
            
            # --- NEXT PHASE ---
            clicked_times = 0
            
            next_btn = page.locator("a:has-text('Next Page')")
            
            if next_btn.is_visible():
                next_btn.click()
                page.wait_for_timeout(1500) 
                clicked_times += 1
            else:
                print("No more buttons found. Reached end of list.")
                break
        
            if clicked_times == 0:
                print("Scraping Complete!")
                break

        browser.close()
        print("Browser closed.")

if __name__ == "__main__":
    print("Checking Database...")
    create_db_tables()
    
    print("Starting Scraper...")
    scrape_fitgirl_az()
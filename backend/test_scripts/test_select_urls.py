from logging_config import setup_logging
setup_logging()

import asyncio
import json
import time
from services.select_urls.select_urls import select_urls

async def test_select_urls():
    items_with_urls = [
        {
            "question": "What is the maternal mortality ratio in India?",
            "query": "India maternal mortality ratio statistics",
            "urls": [
                {
                    "title": "Maternal mortality ratio - Wikipedia",
                    "href": "https://en.wikipedia.org/wiki/Maternal_mortality_ratio",
                    "body": "The maternal mortality ratio (MMR) is the number of maternal deaths per 100,000 live births in a given time period."
                },
                {
                    "title": "India Maternal Mortality - WHO Official Report",
                    "href": "https://www.who.int/india/health-topics/maternal-mortality",
                    "body": "According to WHO data, India has made significant progress in reducing maternal mortality from 570 per 100,000 live births in 1990 to 97 in 2015."
                },
                {
                    "title": "Indian Ministry of Health Maternal Health Programs",
                    "href": "https://main.mohfw.gov.in/maternal-health",
                    "body": "Official government programs and statistics on maternal health initiatives in India including NRHM and RMNCH+A."
                },
                {
                    "title": "Maternal Mortality in India - Medium Blog",
                    "href": "https://medium.com/@healthblogger/maternal-mortality-india",
                    "body": "Personal insights and blog post about maternal mortality challenges in rural India."
                },
                {
                    "title": "India's Maternal Health Crisis - Twitter Thread",
                    "href": "https://twitter.com/healthactivist/maternal-india",
                    "body": "Social media discussion about maternal health issues."
                },
                {
                    "title": "Lancet Study: Maternal Mortality Trends in South Asia",
                    "href": "https://www.thelancet.com/journals/lancet/article/maternal-mortality-south-asia",
                    "body": "Peer-reviewed research showing maternal mortality trends across South Asian countries including India."
                },
                {
                    "title": "World Bank Data - India Health Indicators",
                    "href": "https://data.worldbank.org/indicator/SP.DYN.CDRT.IN?locations=IN",
                    "body": "World Bank official statistics on health indicators including maternal mortality for India."
                },
                {
                    "title": "India Maternal Mortality Reddit Discussion",
                    "href": "https://reddit.com/r/India/maternal-mortality-discussion",
                    "body": "Reddit forum discussing personal experiences and opinions about maternal health."
                }
            ]
        },
        {
            "question": "What is the fertility rate decline in Muslim-majority countries?",
            "query": "Muslim-majority countries fertility rate decline since 1990",
            "urls": [
                {
                    "title": "List of countries by total fertility rate - Wikipedia",
                    "href": "https://en.wikipedia.org/wiki/List_of_countries_by_total_fertility_rate",
                    "body": "Comprehensive Wikipedia list showing fertility rates by country."
                },
                {
                    "title": "Fertility Decline in the Muslim World - Hoover Institution",
                    "href": "https://www.hoover.org/research/fertility-decline-muslim-world",
                    "body": "Academic research from Hoover Institution showing 22 Muslim-majority countries experienced 50% or more fertility decline between 1990-2015."
                },
                {
                    "title": "Muslim Countries Fertility Rates - Random Blog",
                    "href": "https://randomstats.blog.com/muslim-fertility-rates",
                    "body": "Informal blog post about fertility statistics in Muslim countries."
                },
                {
                    "title": "Pew Research Center Study - Muslim Demographics",
                    "href": "https://www.pewresearch.org/religion/2017/muslim-demographics/",
                    "body": "Official Pew Research Center analysis on Muslim population demographics and fertility trends."
                },
                {
                    "title": "Facebook Group - Muslim Women Health Issues",
                    "href": "https://facebook.com/groups/muslim-women-health",
                    "body": "Social media group discussing personal health experiences."
                },
                {
                    "title": "Fertility Trends - Factually Fact-Check",
                    "href": "https://factually.co/fact-checks/fertility-trends-muslim-majority-countries",
                    "body": "Fact-checking organization analysis showing Muslim-majority countries fertility decline from 4.3 to 2.9 between 1990-2015."
                },
                {
                    "title": "UN Population Division - World Population Prospects",
                    "href": "https://population.un.org/wpp/",
                    "body": "Official UN data on global fertility rates and demographic trends."
                }
            ]
        },
        {
            "question": "What is triple talaq in Islamic law?",
            "query": "triple talaq Islamic law definition India",
            "urls": [
                {
                    "title": "Triple Talaq - Wikipedia",
                    "href": "https://en.wikipedia.org/wiki/Triple_talaq",
                    "body": "Wikipedia explanation of triple talaq in Islamic jurisprudence."
                },
                {
                    "title": "Indian Supreme Court Triple Talaq Judgment 2022",
                    "href": "https://supremecourt.gov.in/judgments/triple-talaq-case",
                    "body": "Official Supreme Court of India judgment declaring triple talaq unconstitutional and void."
                },
                {
                    "title": "My Personal Opinion on Triple Talaq - Medium",
                    "href": "https://medium.com/@islamiclaw/triple-talaq-opinion",
                    "body": "Personal blog post with subjective views on triple talaq practices."
                },
                {
                    "title": "Triple Talaq in Islamic Jurisprudence - Al-Azhar University",
                    "href": "https://www.azhar.edu.eg/research/triple-talaq",
                    "body": "Academic research from Al-Azhar University on triple talaq in Islamic legal tradition."
                },
                {
                    "title": "BBC News - India Triple Talaq Ban",
                    "href": "https://bbc.com/news/world-asia-india-triple-talaq",
                    "body": "BBC reporting on India's legal move to ban triple talaq and international implications."
                },
                {
                    "title": "What is Triple Talaq - Quora Discussion",
                    "href": "https://quora.com/What-is-triple-talaq",
                    "body": "Quora forum with user-generated answers about triple talaq."
                }
            ]
        }
    ]
    
    print("Input items with URLs:")
    for i, item in enumerate(items_with_urls, 1):
        print(f"\n{i}. Query: {item['query']}")
        print(f"   Total URLs: {len(item['urls'])}")
        for j, url in enumerate(item['urls'], 1):
            print(f"     [{j}] {url['title']}")
    
    print("\n" + "="*70)
    print("Selecting top 3 URLs for each item...")
    print("="*70 + "\n")
    
    start_time = time.time()
    try:
        result = await select_urls(items_with_urls)
        elapsed = time.time() - start_time
        
        print(f"Latency: {elapsed:.2f}s\n")
        
        for i, item in enumerate(result, 1):
            print(f"{i}. Query: {item['query']}")
            print(f"   Selected URLs ({len(item.get('selected_urls', []))}): ")
            for j, url in enumerate(item.get('selected_urls', []), 1):
                print(f"     [{j}] {url}")
            print()
    
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Latency: {elapsed:.2f}s")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_select_urls())

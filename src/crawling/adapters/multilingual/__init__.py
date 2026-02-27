"""Asia-Pacific + Europe/ME adapters (Groups F+G: 13 sites).

Group F (Asia-Pacific): people, globaltimes, scmp, taiwannews, yomiuri, thehindu
Group G (Europe/ME): thesun, bild, lemonde, themoscowtimes, arabnews, aljazeera, israelhayom
Languages: zh, ja, de, fr, en

Reference:
    Step 6: crawl-strategy-asia.md (Group F), crawl-strategy-global.md (Group G).
"""

# Group F: Asia-Pacific
from src.crawling.adapters.multilingual.people import PeopleAdapter
from src.crawling.adapters.multilingual.globaltimes import GlobalTimesAdapter
from src.crawling.adapters.multilingual.scmp import SCMPAdapter
from src.crawling.adapters.multilingual.taiwannews import TaiwanNewsAdapter
from src.crawling.adapters.multilingual.yomiuri import YomiuriAdapter
from src.crawling.adapters.multilingual.thehindu import TheHinduAdapter

# Group G: Europe/ME
from src.crawling.adapters.multilingual.thesun import TheSunAdapter
from src.crawling.adapters.multilingual.bild import BildAdapter
from src.crawling.adapters.multilingual.lemonde import LeMondeAdapter
from src.crawling.adapters.multilingual.themoscowtimes import MoscowTimesAdapter
from src.crawling.adapters.multilingual.arabnews import ArabNewsAdapter
from src.crawling.adapters.multilingual.aljazeera import AlJazeeraAdapter
from src.crawling.adapters.multilingual.israelhayom import IsraelHayomAdapter

# Registry mapping SITE_ID -> adapter class
MULTILINGUAL_ADAPTERS: dict[str, type] = {
    "people": PeopleAdapter,
    "globaltimes": GlobalTimesAdapter,
    "scmp": SCMPAdapter,
    "taiwannews": TaiwanNewsAdapter,
    "yomiuri": YomiuriAdapter,
    "thehindu": TheHinduAdapter,
    "thesun": TheSunAdapter,
    "bild": BildAdapter,
    "lemonde": LeMondeAdapter,
    "themoscowtimes": MoscowTimesAdapter,
    "arabnews": ArabNewsAdapter,
    "aljazeera": AlJazeeraAdapter,
    "israelhayom": IsraelHayomAdapter,
}

__all__ = [
    "PeopleAdapter",
    "GlobalTimesAdapter",
    "SCMPAdapter",
    "TaiwanNewsAdapter",
    "YomiuriAdapter",
    "TheHinduAdapter",
    "TheSunAdapter",
    "BildAdapter",
    "LeMondeAdapter",
    "MoscowTimesAdapter",
    "ArabNewsAdapter",
    "AlJazeeraAdapter",
    "IsraelHayomAdapter",
    "MULTILINGUAL_ADAPTERS",
]

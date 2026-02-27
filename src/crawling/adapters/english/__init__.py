"""English-language Western adapters (Group E: 12 sites).

Sites: marketwatch, voakorea, huffpost, nytimes, ft, wsj,
       latimes, buzzfeed, nationalpost, cnn, bloomberg, afmedios

Paywall classification:
    Hard paywall (title-only): nytimes, ft, wsj, bloomberg
    Soft-metered paywall:      marketwatch, latimes, nationalpost
    No paywall:                voakorea, huffpost, buzzfeed, cnn, afmedios

Language notes:
    - voakorea: Korean-language (ko) VOA service
    - afmedios: Spanish-language (es) Mexican outlet
    - All others: English (en)
"""

from src.crawling.adapters.english.marketwatch import MarketWatchAdapter
from src.crawling.adapters.english.voakorea import VOAKoreaAdapter
from src.crawling.adapters.english.huffpost import HuffPostAdapter
from src.crawling.adapters.english.nytimes import NYTimesAdapter
from src.crawling.adapters.english.ft import FTAdapter
from src.crawling.adapters.english.wsj import WSJAdapter
from src.crawling.adapters.english.latimes import LATimesAdapter
from src.crawling.adapters.english.buzzfeed import BuzzFeedAdapter
from src.crawling.adapters.english.nationalpost import NationalPostAdapter
from src.crawling.adapters.english.cnn import CNNAdapter
from src.crawling.adapters.english.bloomberg import BloombergAdapter
from src.crawling.adapters.english.afmedios import AFMediosAdapter

__all__ = [
    "MarketWatchAdapter",
    "VOAKoreaAdapter",
    "HuffPostAdapter",
    "NYTimesAdapter",
    "FTAdapter",
    "WSJAdapter",
    "LATimesAdapter",
    "BuzzFeedAdapter",
    "NationalPostAdapter",
    "CNNAdapter",
    "BloombergAdapter",
    "AFMediosAdapter",
]

# Adapter registry mapping source_id -> adapter class
ENGLISH_ADAPTERS: dict[str, type] = {
    "marketwatch": MarketWatchAdapter,
    "voakorea": VOAKoreaAdapter,
    "huffpost": HuffPostAdapter,
    "nytimes": NYTimesAdapter,
    "ft": FTAdapter,
    "wsj": WSJAdapter,
    "latimes": LATimesAdapter,
    "buzzfeed": BuzzFeedAdapter,
    "nationalpost": NationalPostAdapter,
    "cnn": CNNAdapter,
    "bloomberg": BloombergAdapter,
    "afmedios": AFMediosAdapter,
}

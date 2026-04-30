from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import base64
import re
from typing import Dict, List
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from services.llm_service import LLMService


class SearchService:
    SEARCH_TIMEOUT_SECONDS = 8

    LOW_SIGNAL_DOMAINS = {
        "www.bing.com",
        "bing.com",
        "www.zhihu.com",
        "zhihu.com",
        "zhidao.baidu.com",
        "www.linkedin.com",
        "linkedin.com",
        "www.pressreader.com",
        "pressreader.com",
        "www.justdial.com",
        "justdial.com",
        "es.ccm.net",
        "ccm.net",
        "foro.elchapuzasinformatico.com",
    }

    COMPANY_RESEARCH_URLS = {
        "華碩": [
            {
                "title": "ASUS Investor Relations - Financial Reports",
                "url": "https://www.asus.com/EVENT/Investor/C/ir_report",
                "snippet": "Official ASUS investor relations page for annual reports, financial reports, consolidated financial statements, subsidiaries, income tax, and management discussion.",
            },
            {
                "title": "ASUS 2024 Annual Report",
                "url": "https://www.asus.com/EVENT/Investor/Content/attachment/2024_Annual_Report_ch.pdf",
                "snippet": "Official ASUS annual report covering consolidated financial statements, subsidiaries, income tax, related party disclosures, overseas operations, and risk factors.",
            },
            {
                "title": "ASUS Consolidated Financial Report 2025 Q2",
                "url": "https://www.asus.com/EVENT/Investor/Content/attachment/114Q2%20%E8%8F%AF%E7%A2%A9%E8%B2%A1%E5%A0%B1(%E5%90%88%E4%BD%B5).pdf",
                "snippet": "Official ASUS consolidated financial report for ASUSTeK Computer Inc. and subsidiaries, including income tax, consolidated statements, and subsidiary financial disclosures.",
            },
            {
                "title": "ASUS Related Party Transactions Management Regulation",
                "url": "https://www.asus.com/EVENT/Investor/Content/attachment_en/Related%20Party%20Transactions%20Management%20Regulation.pdf",
                "snippet": "Official ASUS regulation for related party transactions, group governance, subsidiaries, affiliates, and transaction controls.",
            },
            {
                "title": "ASUS Corporate Governance",
                "url": "https://www.asus.com/EVENT/Investor/C/ir_corporate_governance",
                "snippet": "Official ASUS corporate governance information relevant to group governance, risk oversight, subsidiaries, and compliance.",
            },
            {
                "title": "ASUS Sustainability and ESG Information",
                "url": "https://www.asus.com/EVENT/Investor/C/ir_sustainability",
                "snippet": "Official ASUS sustainability information relevant to tax governance, supply chain, global operations, and compliance disclosures.",
            },
        ],
        "華碩電腦": [],
        "asus": [],
        "asustek": [],
        "台積電": [
            {
                "title": "TSMC Annual Reports",
                "url": "https://www.tsmc.com/english/aboutTSMC/dc_annual_report",
                "snippet": "Official TSMC annual reports page for investor information, financial statements, subsidiaries, income tax, and risk disclosures.",
            },
            {
                "title": "TSMC 2024 Annual Report",
                "url": "https://investor.tsmc.com/sites/ir/annual-report/2024/2024%20Annual%20Report-E.pdf",
                "snippet": "Official TSMC 2024 annual report with income tax expense, deferred tax, subsidiaries, tax incentives, overseas operations, and risk factors.",
            },
            {
                "title": "TSMC 2024 Annual Report Website",
                "url": "https://investor.tsmc.com/static/annualReports/2024/english/index.html",
                "snippet": "Official TSMC annual report website covering financial statements, income tax expenses, subsidiaries, and management discussion.",
            },
            {
                "title": "TSMC SEC Filings",
                "url": "https://investor.tsmc.com/english/sec-filings",
                "snippet": "Official TSMC SEC filings page for Form 20-F and cross-border disclosure documents.",
            },
        ],
        "鴻海": [
            {
                "title": "Hon Hai Technology Group Annual Reports",
                "url": "https://www.foxconn.com/en-us/investor-relations/financial-information/reports?category=annual",
                "snippet": "Official Hon Hai / Foxconn annual reports page for consolidated financial statements, subsidiaries, income tax, and risk disclosures.",
            },
            {
                "title": "Hon Hai Tax Policy and Management Procedures",
                "url": "https://image.honhai.com/upload/global/Tax%20Policy%20and%20Management%20Procedures_EN_20240701_3727.pdf",
                "snippet": "Official Hon Hai tax policy covering subsidiaries, tax filings, transaction tax impact, external advisors, governance, and regulatory review.",
            },
            {
                "title": "Hon Hai / Foxconn Quarterly and Annual Reports",
                "url": "https://www.foxconn.com.cn/en-us/investor-relations/financial-information/reports",
                "snippet": "Official Hon Hai / Foxconn reports page for quarterly consolidated reports, annual reports, financial information, and subsidiaries.",
            },
        ],
        "toyota": [
            {
                "title": "Toyota Tax Policy",
                "url": "https://global.toyota/pages/global_toyota/sustainability/esg/tax-policy_en.pdf",
                "snippet": "Official Toyota tax policy covering transfer pricing, double taxation, tax treaties, subsidiaries, OECD principles, and cross-border tax governance.",
            },
            {
                "title": "Toyota Sustainability Policies and Guidelines",
                "url": "https://global.toyota/en/sustainability/report/policies_guidelines/",
                "snippet": "Official Toyota sustainability policy library with taxation, compliance, supply chain, subsidiaries, and governance policy materials.",
            },
            {
                "title": "Toyota Global Official Website",
                "url": "https://global.toyota/en/",
                "snippet": "Official Toyota Motor Corporation global website for corporate, sustainability, investor, subsidiaries, and policy information.",
            },
        ],
    }

    CROSS_BORDER_REFERENCE_RESULTS = [
        {
            "title": "Deloitte Taiwan - Cross-Border Tax Governance Risks",
            "url": "https://www.deloitte.com/tw/tc/services/tax/perspectives/2026-outlook-international-tax.html",
            "snippet": "Professional tax reference covering cross-border tax governance, multinational group compliance, global operations, and risk response.",
        },
        {
            "title": "PwC Taiwan - CFC and Global Minimum Tax for Multinational Groups",
            "url": "https://www.pwc.tw/zh/news/press-release/press-20240409.html",
            "snippet": "Professional tax reference covering CFC rules, global minimum tax, Pillar Two, multinational groups, subsidiaries, and compliance actions.",
        },
        {
            "title": "OECD BEPS and Pillar Two Global Minimum Tax",
            "url": "https://www.oecd.org/tax/beps/",
            "snippet": "Official OECD reference for BEPS, Pillar Two, global minimum tax, transfer pricing, and international tax risk.",
        },
    ]

    COMPANY_ALIAS_MAP = {
        "華碩": ["ASUS", "ASUSTeK", "ASUSTeK Computer", "華碩電腦"],
        "華碩電腦": ["ASUS", "ASUSTeK", "ASUSTeK Computer", "華碩"],
        "asus": ["ASUSTeK", "ASUSTeK Computer", "華碩", "華碩電腦"],
        "asustek": ["ASUS", "ASUSTeK Computer", "華碩", "華碩電腦"],
        "台積電": ["TSMC", "Taiwan Semiconductor", "Taiwan Semiconductor Manufacturing", "台灣積體電路製造"],
        "台灣積體電路": ["TSMC", "Taiwan Semiconductor", "Taiwan Semiconductor Manufacturing", "台積電"],
        "tsmc": ["台積電", "台灣積體電路製造", "Taiwan Semiconductor", "Taiwan Semiconductor Manufacturing"],
        "鴻海": ["Foxconn", "富士康", "Foxconn Technology Group", "Hon Hai", "Hon Hai Precision", "鴻海精密"],
        "鴻海精密": ["Foxconn", "富士康", "Foxconn Technology Group", "Hon Hai", "Hon Hai Precision", "鴻海"],
        "富士康": ["Foxconn", "Foxconn Technology Group", "Hon Hai", "Hon Hai Precision", "鴻海", "鴻海精密"],
        "foxconn": ["鴻海", "鴻海精密", "富士康", "Hon Hai", "Hon Hai Precision"],
        "hon hai": ["鴻海", "鴻海精密", "富士康", "Foxconn", "Foxconn Technology Group", "Hon Hai Precision"],
        "聯發科": ["MediaTek", "MediaTek Inc", "聯發科技"],
        "聯發科技": ["MediaTek", "MediaTek Inc", "聯發科"],
        "mediatek": ["聯發科", "聯發科技", "MediaTek Inc"],
        "宏碁": ["Acer", "Acer Inc", "Acer Incorporated"],
        "acer": ["宏碁", "Acer Inc", "Acer Incorporated"],
        "和碩": ["Pegatron", "Pegatron Corporation", "和碩聯合科技"],
        "pegatron": ["和碩", "和碩聯合科技", "Pegatron Corporation"],
        "廣達": ["Quanta", "Quanta Computer", "廣達電腦"],
        "quanta": ["廣達", "廣達電腦", "Quanta Computer"],
        "緯創": ["Wistron", "Wistron Corporation", "緯創資通"],
        "wistron": ["緯創", "緯創資通", "Wistron Corporation"],
        "仁寶": ["Compal", "Compal Electronics", "仁寶電腦"],
        "compal": ["仁寶", "仁寶電腦", "Compal Electronics"],
        "友達": ["AUO", "AU Optronics", "友達光電"],
        "auo": ["友達", "友達光電", "AU Optronics"],
        "群創": ["Innolux", "Innolux Corporation", "群創光電"],
        "innolux": ["群創", "群創光電", "Innolux Corporation"],
        "台達電": ["Delta Electronics", "Delta", "台達電子"],
        "delta electronics": ["台達電", "台達電子", "Delta"],
        "聯電": ["UMC", "United Microelectronics", "聯華電子"],
        "umc": ["聯電", "聯華電子", "United Microelectronics"],
        "toyota": ["Toyota Motor", "Toyota Motor Corporation", "トヨタ自動車"],
        "toyota motor": ["Toyota", "Toyota Motor Corporation", "トヨタ自動車"],
    }

    COMPANY_DOMAIN_MAP = {
        "華碩": ["asus.com", "asus.com.cn"],
        "華碩電腦": ["asus.com", "asus.com.cn"],
        "asus": ["asus.com", "asus.com.cn"],
        "asustek": ["asus.com", "asus.com.cn"],
        "台積電": ["tsmc.com"],
        "tsmc": ["tsmc.com"],
        "鴻海": ["honhai.com", "foxconn.com"],
        "foxconn": ["foxconn.com", "honhai.com"],
        "hon hai": ["honhai.com", "foxconn.com"],
        "聯發科": ["mediatek.com"],
        "mediatek": ["mediatek.com"],
        "宏碁": ["acer.com"],
        "acer": ["acer.com"],
        "和碩": ["pegatroncorp.com"],
        "pegatron": ["pegatroncorp.com"],
        "廣達": ["quantatw.com"],
        "quanta": ["quantatw.com"],
        "緯創": ["wistron.com"],
        "wistron": ["wistron.com"],
        "仁寶": ["compal.com"],
        "compal": ["compal.com"],
        "友達": ["auo.com"],
        "auo": ["auo.com"],
        "群創": ["innolux.com"],
        "innolux": ["innolux.com"],
        "台達電": ["deltaww.com"],
        "delta electronics": ["deltaww.com"],
        "聯電": ["umc.com"],
        "umc": ["umc.com"],
        "toyota": ["global.toyota", "toyota.com"],
        "toyota motor": ["global.toyota", "toyota.com"],
    }

    OFFICIAL_TAX_DOMAINS = [
        "oecd.org",
        "ey.com",
        "kpmg.com",
        "deloitte.com",
        "pwc.com",
        "ibfd.org",
        "taxfoundation.org",
        "irs.gov",
        "ec.europa.eu",
        "gov.uk",
        "moj.gov.tw",
        "dot.gov.tw",
        "mof.gov.tw",
    ]

    DISCLOSURE_DOMAINS = [
        "twse.com.tw",
        "mops.twse.com.tw",
        "mopsov.twse.com.tw",
        "annualreports.com",
        "marketscreener.com",
        "sec.gov",
        "reuters.com",
        "stockanalysis.com",
        "companiesmarketcap.com",
    ]

    TAX_KEYPHRASES = [
        "tax",
        "tax reform",
        "tax update",
        "tax risk",
        "tax policy",
        "tax strategy",
        "tax transparency",
        "compliance",
        "filing obligation",
        "effective date",
        "draft regulation",
        "pillar two",
        "transfer pricing",
        "withholding tax",
        "vat",
        "penalty",
        "income tax",
        "income tax expense",
        "deferred tax",
        "tax audit",
        "tax incentives",
        "tax governance",
        "tax litigation",
        "uncertain tax positions",
        "annual report",
        "sustainability report",
        "financial statement",
        "cross-border tax",
        "international tax",
        "global minimum tax",
        "pillar two",
        "beps",
        "permanent establishment",
        "withholding tax",
        "customs duty",
        "tariff",
        "customs valuation",
        "vat",
        "gst",
        "cfc",
        "supply chain",
        "subsidiaries",
        "related party transactions",
        "group structure",
        "consolidated financial statements",
        "affiliate",
        "申報",
        "稅務",
        "稅務風險",
        "稅務治理",
        "稅改",
        "所得稅",
        "營所稅",
        "移轉訂價",
        "關係人交易",
        "跨國稅務",
        "國際租稅",
        "全球最低稅負",
        "支柱二",
        "常設機構",
        "扣繳稅",
        "關稅",
        "進出口稅",
        "海關估價",
        "加值稅",
        "營業稅",
        "受控外國公司",
        "供應鏈",
        "子公司",
        "關係企業",
        "集團架構",
        "合併財務報表",
        "轉投資",
        "主要子公司",
        "年報",
        "財報",
        "永續報告",
        "訴訟",
        "生效",
        "草案",
        "合規",
        "罰則",
    ]

    COMPANY_RESEARCH_TOPICS = [
        "tax risk",
        "tax governance",
        "tax policy",
        "tax strategy",
        "tax transparency",
        "income tax",
        "income tax expense",
        "deferred tax",
        "tax audit",
        "tax incentives",
        "effective tax rate",
        "uncertain tax positions",
        "transfer pricing",
        "tax litigation",
        "tax penalty",
        "cross-border tax",
        "international tax",
        "global minimum tax",
        "pillar two",
        "permanent establishment",
        "withholding tax",
        "customs duty",
        "tariff",
        "vat gst",
        "cfc rules",
        "supply chain tax",
        "annual report",
        "financial statement",
        "sustainability report",
        "subsidiaries",
        "subsidiary tax risk",
        "related party transactions",
        "group structure",
        "consolidated financial statements",
        "affiliate companies",
        "稅務風險",
        "稅務治理",
        "所得稅",
        "有效稅率",
        "移轉訂價",
        "關係人交易",
        "稅務訴訟",
        "裁罰",
        "跨國稅務",
        "國際租稅",
        "全球最低稅負",
        "支柱二",
        "常設機構",
        "扣繳稅",
        "關稅",
        "加值稅",
        "營業稅",
        "受控外國公司",
        "供應鏈稅務",
        "年報",
        "財報",
        "永續報告書",
        "子公司",
        "主要子公司",
        "關係企業",
        "集團架構",
        "合併財務報表",
        "轉投資",
    ]

    SUBSIDIARY_RESEARCH_TOPICS = [
        "subsidiaries tax risk",
        "subsidiary transfer pricing",
        "related party transactions tax",
        "group structure tax",
        "consolidated financial statements income tax",
        "list of subsidiaries annual report",
        "significant subsidiaries tax",
        "affiliate companies tax",
        "overseas subsidiaries tax",
        "子公司 稅務風險",
        "子公司 所得稅",
        "主要子公司 年報",
        "關係企業 交易 所得稅",
        "集團架構 稅務",
        "合併財務報表 所得稅",
        "轉投資 子公司 稅務",
    ]

    TAX_RISK_EVENT_TOPICS = [
        "tax audit",
        "tax investigation",
        "tax probe",
        "tax authority investigation",
        "tax row",
        "tax notice",
        "tax notices",
        "tax assessment",
        "tax demand",
        "tax penalty",
        "tax fine",
        "tax dispute",
        "tax litigation",
        "tax settlement",
        "back tax",
        "tax reassessment",
        "tax compliance risk",
        "transfer pricing audit",
        "transfer pricing dispute",
        "related party transaction audit",
        "customs investigation",
        "customs penalty",
        "tariff impact",
        "tariff risk",
        "anti-dumping duty",
        "countervailing duty",
        "import duty",
        "withholding tax dispute",
        "vat dispute",
        "gst dispute",
        "property tax",
        "land tax",
        "permanent establishment risk",
        "global minimum tax impact",
        "pillar two impact",
        "cfc rule impact",
        "稅務稽查",
        "稅務調查",
        "稅務查核",
        "查稅",
        "查稅結果",
        "稅務及用地",
        "用地調查",
        "稅務裁罰",
        "稅務罰鍰",
        "補稅",
        "欠稅",
        "漏稅",
        "稅務爭議",
        "稅務訴訟",
        "稅局調查",
        "國稅局 查核",
        "虛假計稅",
        "移轉訂價 查核",
        "關係人交易 查核",
        "關稅 衝擊",
        "關稅 風險",
        "反傾銷稅",
        "反補貼稅",
        "海關 稽查",
        "進口稅",
        "扣繳稅 爭議",
        "營業稅 爭議",
        "常設機構 風險",
        "全球最低稅負 影響",
        "支柱二 影響",
        "受控外國公司 影響",
    ]

    TAX_NEWS_DOMAINS = [
        "reuters.com",
        "bloombergtax.com",
        "taxnotes.com",
        "internationaltaxreview.com",
        "tax.thomsonreuters.com",
        "nikkei.com",
        "ft.com",
        "wsj.com",
        "cna.com.tw",
        "taipeitimes.com",
        "digitimes.com",
        "technews.tw",
        "ltn.com.tw",
        "ec.ltn.com.tw",
        "news.ltn.com.tw",
        "rti.org.tw",
        "storm.mg",
        "chinatimes.com",
        "ettoday.net",
        "money.udn.com",
        "ctee.com.tw",
        "yahoo.com",
    ]

    GLOBAL_LOCALES = [
        {"hl": "en-US", "gl": "US", "ceid": "US:en"},
        {"hl": "en-GB", "gl": "GB", "ceid": "GB:en"},
        {"hl": "en-AU", "gl": "AU", "ceid": "AU:en"},
        {"hl": "en-SG", "gl": "SG", "ceid": "SG:en"},
        {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
        {"hl": "zh-HK", "gl": "HK", "ceid": "HK:zh-Hant"},
        {"hl": "en-CA", "gl": "CA", "ceid": "CA:en"},
    ]

    def search(
        self,
        keywords: List[str],
        user_prompt: str = None,
        mode: str = "auto",
        date_range: str = "1m",
        start_date: str = None,
        end_date: str = None,
        max_results: int = 10,
        candidate_urls: List[str] = None,
        source_name: str = "google_news_rss",
        use_ai_query_expansion: bool = True,
        provider: str = "ollama",
        model_name: str = "qwen3:8b"
    ) -> List[Dict]:
        keywords = self._normalize_keywords(keywords)
        query = " ".join(keywords)
        candidate_urls = candidate_urls or []
        source_name = (source_name or "google_news_rss").strip().lower()

        if mode == "manual" and candidate_urls:
            return [
                {
                    "title": url,
                    "url": url,
                    "snippet": user_prompt or "",
                    "source": "manual",
                    "published_at": None,
                    "relevance_score": 1.0
                }
                for url in candidate_urls[:max_results]
            ]

        window = self._resolve_date_window(date_range, start_date, end_date)
        ai_variants = self._build_ai_query_variants(
            keywords=keywords,
            user_prompt=user_prompt,
            provider=provider,
            model_name=model_name,
            enabled=use_ai_query_expansion
        )
        if source_name in {"all", "google_news_rss_global"}:
            results = self._search_google_news_rss_global(
                query=query,
                keywords=keywords,
                user_prompt=user_prompt,
                window=window,
                max_results=max_results,
                ai_variants=ai_variants,
                source_name=source_name
            )
        else:
            results = self._search_multi_source(
                query=query,
                keywords=keywords,
                user_prompt=user_prompt,
                window=window,
                max_results=max_results,
                ai_variants=ai_variants,
                source_name=source_name
        )
        ranked = self._rank_results(results, keywords=keywords, user_prompt=user_prompt)
        filtered = [item for item in ranked if item.get("relevance_score", 0.0) >= 1.0]
        return filtered[:max_results]

    def __init__(self):
        self.llm_service = LLMService()

    def _candidate_limit(self, max_results: int) -> int:
        return min(120, max(25, max_results * 3))

    def _search_google_news_rss(self, query: str, window: Dict[str, datetime], max_results: int) -> List[Dict]:
        when_clause = self._build_google_news_when(window)
        full_query = f"{query} {when_clause}".strip()
        url = f"https://news.google.com/rss/search?q={quote_plus(full_query)}&hl=en-US&gl=US&ceid=US:en"
        return self._fetch_google_news_feed(url=url, max_results=max_results, source_name="google_news_rss")

    def _search_multi_source(
        self,
        query: str,
        keywords: List[str],
        user_prompt: str,
        window: Dict[str, datetime],
        max_results: int,
        ai_variants: List[str],
        source_name: str
    ) -> List[Dict]:
        merged = []
        seen_urls = set()
        candidate_limit = self._candidate_limit(max_results)
        query_variants = self._merge_query_variants(
            keywords=keywords,
            user_prompt=user_prompt,
            ai_variants=ai_variants
        )
        targeted_queries = self._build_official_site_queries(
            keywords=keywords,
            user_prompt=user_prompt,
            query_variants=query_variants
        )
        for item in self._build_seed_results(keywords=keywords, user_prompt=user_prompt):
            self._append_unique_result(merged, seen_urls, item)

        if source_name == "duckduckgo":
            for index, variant in enumerate(query_variants[:5]):
                for item in self._safe_search_call(self._search_duckduckgo_html, variant, max_results):
                    self._append_unique_result(merged, seen_urls, item)
                if index < 2:
                    for item in self._safe_search_call(self._search_duckduckgo_pdf, variant, max_results):
                        self._append_unique_result(merged, seen_urls, item)
                if len(merged) >= candidate_limit:
                    return merged
            for targeted_query in targeted_queries[:18]:
                for item in self._safe_search_call(self._search_duckduckgo_html, targeted_query, max_results):
                    self._append_unique_result(merged, seen_urls, item)
                if len(merged) >= candidate_limit:
                    return merged
            return merged

        if source_name == "bing_web":
            for index, variant in enumerate(query_variants[:5]):
                for item in self._safe_search_call(self._search_bing_web, variant, max_results):
                    self._append_unique_result(merged, seen_urls, item)
                if index < 2:
                    for item in self._safe_search_call(self._search_bing_pdf, variant, max_results):
                        self._append_unique_result(merged, seen_urls, item)
                if len(merged) >= candidate_limit:
                    return merged
            for targeted_query in targeted_queries[:18]:
                for item in self._safe_search_call(self._search_bing_web, targeted_query, max_results):
                    self._append_unique_result(merged, seen_urls, item)
                if len(merged) >= candidate_limit:
                    return merged
            return merged

        if source_name == "google_news_rss":
            for variant in query_variants[:4]:
                for item in self._safe_search_call(self._search_google_news_rss, variant, window, max_results):
                    self._append_unique_result(merged, seen_urls, item)
            return merged

        for index, variant in enumerate(query_variants[:5]):
            for item in self._safe_search_call(self._search_google_news_rss, variant, window, max_results):
                self._append_unique_result(merged, seen_urls, item)
            for item in self._safe_search_call(self._search_duckduckgo_html, variant, max_results):
                self._append_unique_result(merged, seen_urls, item)
            if index < 2:
                for item in self._safe_search_call(self._search_duckduckgo_pdf, variant, max_results):
                    self._append_unique_result(merged, seen_urls, item)
            for item in self._safe_search_call(self._search_bing_news_rss, variant, window, max_results):
                self._append_unique_result(merged, seen_urls, item)
            for item in self._safe_search_call(self._search_bing_web, variant, max_results):
                self._append_unique_result(merged, seen_urls, item)
            if index < 2:
                for item in self._safe_search_call(self._search_bing_pdf, variant, max_results):
                    self._append_unique_result(merged, seen_urls, item)
            if len(merged) >= candidate_limit:
                return merged
        for targeted_query in targeted_queries[:18]:
            for item in self._safe_search_call(self._search_duckduckgo_html, targeted_query, max_results):
                self._append_unique_result(merged, seen_urls, item)
            for item in self._safe_search_call(self._search_bing_web, targeted_query, max_results):
                self._append_unique_result(merged, seen_urls, item)
            if len(merged) >= candidate_limit:
                return merged
        return merged

    def _search_google_news_rss_global(
        self,
        query: str,
        keywords: List[str],
        user_prompt: str,
        window: Dict[str, datetime],
        max_results: int,
        ai_variants: List[str],
        source_name: str
    ) -> List[Dict]:
        query_variants = self._merge_query_variants(
            keywords=keywords,
            user_prompt=user_prompt,
            ai_variants=ai_variants
        )
        merged_items = []
        seen_urls = set()
        candidate_limit = self._candidate_limit(max_results)
        for item in self._build_seed_results(keywords=keywords, user_prompt=user_prompt):
            self._append_unique_result(merged_items, seen_urls, item)
        tax_event_queries = self._build_tax_risk_event_queries(keywords=keywords, user_prompt=user_prompt)
        event_intent = self._has_tax_event_intent(keywords=keywords, user_prompt=user_prompt)

        if source_name == "all":
            if event_intent:
                for event_query in tax_event_queries[:6]:
                    for item in self._safe_search_call(self._search_google_news_archive, event_query, max_results):
                        self._append_unique_result(merged_items, seen_urls, item)
                    if len(merged_items) >= candidate_limit:
                        return merged_items

                for index, event_query in enumerate(tax_event_queries[:24]):
                    if index < 8:
                        for item in self._safe_search_call(self._search_google_news_rss, event_query, window, max_results):
                            self._append_unique_result(merged_items, seen_urls, item)
                        for item in self._safe_search_call(self._search_bing_news_rss, event_query, window, max_results):
                            self._append_unique_result(merged_items, seen_urls, item)
                    for item in self._safe_search_call(self._search_duckduckgo_html, event_query, max_results):
                        self._append_unique_result(merged_items, seen_urls, item)
                    if index < 12:
                        for item in self._safe_search_call(self._search_bing_web, event_query, max_results):
                            self._append_unique_result(merged_items, seen_urls, item)
                    if len(merged_items) >= candidate_limit:
                        return merged_items

            for index, variant in enumerate(query_variants[:4]):
                for item in self._safe_search_call(self._search_duckduckgo_html, variant, max_results):
                    self._append_unique_result(merged_items, seen_urls, item)
                if index < 4:
                    for item in self._safe_search_call(self._search_duckduckgo_pdf, variant, max_results):
                        self._append_unique_result(merged_items, seen_urls, item)
                for item in self._safe_search_call(self._search_bing_web, variant, max_results):
                    self._append_unique_result(merged_items, seen_urls, item)
                if index < 3:
                    for item in self._safe_search_call(self._search_bing_pdf, variant, max_results):
                        self._append_unique_result(merged_items, seen_urls, item)
                if len(merged_items) >= candidate_limit:
                    return merged_items

            if not event_intent:
                for index, event_query in enumerate(tax_event_queries[:12]):
                    for item in self._safe_search_call(self._search_google_news_rss, event_query, window, max_results):
                        self._append_unique_result(merged_items, seen_urls, item)
                    for item in self._safe_search_call(self._search_bing_news_rss, event_query, window, max_results):
                        self._append_unique_result(merged_items, seen_urls, item)
                    for item in self._safe_search_call(self._search_duckduckgo_html, event_query, max_results):
                        self._append_unique_result(merged_items, seen_urls, item)
                    if index < 6:
                        for item in self._safe_search_call(self._search_bing_web, event_query, max_results):
                            self._append_unique_result(merged_items, seen_urls, item)
                    if len(merged_items) >= candidate_limit:
                        return merged_items

            targeted_queries = self._build_official_site_queries(
                keywords=keywords,
                user_prompt=user_prompt,
                query_variants=query_variants
            )
            for targeted_query in targeted_queries[:12]:
                for item in self._safe_search_call(self._search_duckduckgo_html, targeted_query, max_results):
                    self._append_unique_result(merged_items, seen_urls, item)
                for item in self._safe_search_call(self._search_bing_web, targeted_query, max_results):
                    self._append_unique_result(merged_items, seen_urls, item)
                if len(merged_items) >= candidate_limit:
                    return merged_items

        per_locale_limit = max(4, min(max_results, 8)) if source_name == "all" else max(6, min(max_results, 12))
        news_variants = self._merge_news_variants(
            query_variants=query_variants,
            tax_event_queries=tax_event_queries,
            limit=5 if source_name == "all" else 10
        )
        locales = self.GLOBAL_LOCALES[:3] if source_name == "all" else self.GLOBAL_LOCALES
        for locale in locales:
            for variant in news_variants:
                when_clause = self._build_google_news_when(window)
                full_query = f"{variant} {when_clause}".strip()
                url = (
                    "https://news.google.com/rss/search"
                    f"?q={quote_plus(full_query)}"
                    f"&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
                )
                try:
                    items = self._fetch_google_news_feed(
                        url=url,
                        max_results=per_locale_limit,
                        source_name=f"google_news_rss:{locale['gl']}"
                    )
                except Exception:
                    continue

                for item in items:
                    normalized_url = (item.get("url") or "").strip().lower()
                    if not normalized_url or normalized_url in seen_urls:
                        continue
                    seen_urls.add(normalized_url)
                    merged_items.append(item)

                if len(merged_items) >= max_results * 3:
                    break
            if len(merged_items) >= candidate_limit:
                break

        return merged_items

    def _build_official_site_queries(
        self,
        keywords: List[str],
        user_prompt: str,
        query_variants: List[str]
    ) -> List[str]:
        aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        tax_topics = [
            "tax risk",
            "tax reform",
            "filing obligation",
            "effective date",
            "draft regulation",
            "transfer pricing",
            "pillar two",
        ]

        queries = []
        company_queries = self._build_company_research_queries(aliases)
        queries.extend(company_queries)

        for alias in aliases[:5]:
            for topic in tax_topics[:4]:
                queries.append(f"\"{alias}\" {topic}")

        for domain in self.OFFICIAL_TAX_DOMAINS:
            for variant in query_variants[:4]:
                queries.append(f"site:{domain} {variant}")
            for alias in aliases[:3]:
                queries.append(f"site:{domain} \"{alias}\" tax")
                queries.append(f"site:{domain} \"{alias}\" filetype:pdf")

        normalized = []
        seen = set()
        for query in queries:
            cleaned = " ".join(query.split()).strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized

    def _build_company_research_queries(self, aliases: List[str]) -> List[str]:
        queries = []
        for alias in aliases[:8]:
            queries.append(f"{alias} annual report tax subsidiaries")
            queries.append(f"{alias} financial statements income tax")
            queries.append(f"{alias} sustainability report tax governance")
            queries.append(f"{alias} related party transactions tax")
            queries.append(f"{alias} transfer pricing subsidiaries")
            queries.append(f"{alias} group structure subsidiaries")
            queries.append(f"{alias} 年報 稅務 子公司")
            queries.append(f"{alias} 財報 所得稅 關係企業")
            queries.append(f"{alias} 永續報告 稅務治理")
            queries.append(f"{alias} 轉投資 子公司 稅務")
            queries.append(f"\"{alias}\" filetype:pdf annual report tax")
            queries.append(f"\"{alias}\" filetype:pdf financial statements income tax")
            queries.append(f"\"{alias}\" filetype:pdf subsidiaries")
            queries.append(f"\"{alias}\" filetype:pdf related party transactions")

        disclosure_domains = self._disclosure_domains_for_aliases(aliases)
        for domain in disclosure_domains:
            for alias in aliases[:6]:
                queries.append(f"site:{domain} {alias} annual report tax")
                queries.append(f"site:{domain} {alias} financial statements income tax")
                queries.append(f"site:{domain} {alias} subsidiaries")
                queries.append(f"site:{domain} {alias} related party transactions")
                queries.append(f"site:{domain} {alias} 年報 稅務")
                queries.append(f"site:{domain} {alias} 子公司")
                queries.append(f"site:{domain} {alias} filetype:pdf")

        for alias in aliases[:8]:
            for topic in self.COMPANY_RESEARCH_TOPICS[:16]:
                queries.append(f"\"{alias}\" {topic}")
            for topic in self.SUBSIDIARY_RESEARCH_TOPICS[:12]:
                queries.append(f"\"{alias}\" {topic}")
            queries.append(f"\"{alias}\" 年報 稅務")
            queries.append(f"\"{alias}\" 永續報告 稅務治理")
            queries.append(f"\"{alias}\" 子公司 稅務")
            queries.append(f"\"{alias}\" 關係企業 所得稅")
        return queries

    def _build_tax_risk_event_queries(self, keywords: List[str], user_prompt: str = None) -> List[str]:
        aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        queries = []
        text = " ".join((keywords or []) + [user_prompt or ""]).lower()
        explicit_topics = [
            topic
            for topic in self.TAX_RISK_EVENT_TOPICS
            if topic.lower() in text
        ]
        fallback_topics = [
            "稅務調查",
            "查稅",
            "稅務稽查",
            "稅務及用地",
            "查稅結果",
            "虛假計稅",
            "tax audit",
            "tax investigation",
            "tax penalty",
            "tax dispute",
            "tax row",
            "tax notice",
            "property tax",
            "transfer pricing audit",
            "customs investigation",
            "tariff impact",
            "anti-dumping duty",
            "global minimum tax impact",
            "pillar two impact",
            "查稅",
            "稅務及用地",
            "稅務裁罰",
            "補稅",
            "移轉訂價 查核",
            "關稅 衝擊",
            "反傾銷稅",
            "全球最低稅負 影響",
        ]
        priority_topics = []
        seen_topics = set()
        for topic in explicit_topics + fallback_topics:
            lowered_topic = topic.lower()
            if lowered_topic in seen_topics:
                continue
            seen_topics.add(lowered_topic)
            priority_topics.append(topic)

        for topic in priority_topics:
            for alias in aliases[:6]:
                if len(alias) <= 24:
                    queries.append(f"{alias} {topic}")
            for alias in aliases[:6]:
                queries.append(f"\"{alias}\" {topic}")

        for alias in aliases[:4]:
            for domain in self.TAX_NEWS_DOMAINS[:10]:
                queries.append(f"site:{domain} \"{alias}\" tax")
                queries.append(f"site:{domain} \"{alias}\" tariff")
                queries.append(f"site:{domain} \"{alias}\" tax audit")

        normalized = []
        seen = set()
        for query in queries:
            cleaned = " ".join(query.split()).strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized[:80]

    def _merge_news_variants(self, query_variants: List[str], tax_event_queries: List[str], limit: int) -> List[str]:
        merged = []
        seen = set()
        for query in tax_event_queries[: max(0, limit - 2)] + query_variants[:limit]:
            lowered = query.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            merged.append(query)
            if len(merged) >= limit:
                break
        return merged

    def _disclosure_domains_for_aliases(self, aliases: List[str]) -> List[str]:
        domains = list(self.DISCLOSURE_DOMAINS)
        seen = {domain.lower() for domain in domains}
        for alias in aliases:
            lowered = alias.lower()
            for key, mapped_domains in self.COMPANY_DOMAIN_MAP.items():
                if key.lower() not in lowered:
                    continue
                for domain in mapped_domains:
                    if domain.lower() in seen:
                        continue
                    seen.add(domain.lower())
                    domains.insert(0, domain)
        return domains

    def _build_seed_results(self, keywords: List[str], user_prompt: str = None) -> List[Dict]:
        aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        seeds = []
        seen_urls = set()

        for alias in aliases:
            lowered_alias = alias.lower()
            for key, entries in self.COMPANY_RESEARCH_URLS.items():
                lowered_key = key.lower()
                if lowered_key not in lowered_alias and lowered_alias not in lowered_key:
                    continue
                effective_entries = entries or self.COMPANY_RESEARCH_URLS.get("華碩", [])
                for entry in effective_entries:
                    url = entry["url"]
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    seeds.append({
                        "title": entry["title"],
                        "url": url,
                        "snippet": entry["snippet"],
                        "source": "official_seed",
                        "published_at": None,
                        "relevance_score": 0.0,
                    })

        primary_alias = aliases[0] if aliases else "Company"
        for domain in self._company_domains_for_aliases(aliases):
            url = f"https://{domain}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            seeds.append({
                "title": f"{primary_alias} Official Company Website - {domain}",
                "url": url,
                "snippet": (
                    f"Official company domain for {primary_alias}. Use this as a fallback source for "
                    "investor relations, annual reports, financial statements, sustainability reports, "
                    "subsidiaries, related party transactions, income tax, tax governance, and cross-border tax risk."
                ),
                "source": "official_domain_seed",
                "published_at": None,
                "relevance_score": 0.0,
            })

        if self._needs_cross_border_references(keywords=keywords, user_prompt=user_prompt):
            for entry in self.CROSS_BORDER_REFERENCE_RESULTS:
                url = entry["url"]
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                seeds.append({
                    "title": entry["title"],
                    "url": url,
                    "snippet": entry["snippet"],
                    "source": "reference_seed",
                    "published_at": None,
                    "relevance_score": 0.0,
                })

        return seeds

    def _company_domains_for_aliases(self, aliases: List[str]) -> List[str]:
        domains = []
        seen = set()
        for alias in aliases:
            lowered_alias = alias.lower()
            for key, mapped_domains in self.COMPANY_DOMAIN_MAP.items():
                lowered_key = key.lower()
                if lowered_key not in lowered_alias and lowered_alias not in lowered_key:
                    continue
                for domain in mapped_domains:
                    normalized = domain.lower()
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    domains.append(domain)
        return domains

    def _needs_cross_border_references(self, keywords: List[str], user_prompt: str = None) -> bool:
        text = " ".join(keywords + [user_prompt or ""]).lower()
        terms = [
            "跨國",
            "國際",
            "全球最低稅負",
            "支柱二",
            "常設機構",
            "扣繳稅",
            "關稅",
            "供應鏈",
            "cross-border",
            "international tax",
            "global minimum tax",
            "pillar two",
            "permanent establishment",
            "withholding tax",
            "customs",
            "tariff",
        ]
        return any(term.lower() in text for term in terms)

    def _extract_entity_aliases(self, keywords: List[str], user_prompt: str = None) -> List[str]:
        raw_terms = keywords + re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9&._-]{2,}", user_prompt or "")
        aliases = []
        for term in raw_terms:
            cleaned = " ".join(str(term).split()).strip()
            if not cleaned:
                continue
            aliases.extend(self._split_compact_topic_query(cleaned))
            aliases.extend(self._expand_known_company_aliases(cleaned))
            aliases.extend(self._expand_generic_company_aliases(cleaned))
            aliases.append(self._clean_entity_alias(cleaned))
            aliases.extend(self._split_compact_topic_query(cleaned))
            aliases.extend(self._expand_company_suffix_aliases(cleaned))
            aliases.extend(self._expand_group_entity_aliases(cleaned))

        normalized = []
        seen = set()
        for alias in aliases:
            if self._is_low_value_alias(alias):
                continue
            lowered = alias.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(alias)
        return normalized[:16]

    def _clean_entity_alias(self, term: str) -> str:
        cleaned = " ".join(str(term).split()).strip()
        cleaned = re.sub(r"^(查詢|搜尋|搜索|研究|分析|關於|有關|包含|包括|涵蓋)", "", cleaned, flags=re.IGNORECASE)
        for _ in range(4):
            previous = cleaned.strip(" -_，,。")
            cleaned = previous
            cleaned = re.sub(r"(稅務風險|稅務治理|稅務稽查|稅務調查|稅務查核|稅務裁罰|稅務罰鍰|稅務爭議|稅務訴訟|稅務及用地|用地調查|查稅結果|查稅|虛假計稅|稅務|風險|稽查|調查|查核|裁罰|罰鍰|補稅|欠稅|漏稅|爭議|所得稅|營所稅|移轉訂價|關係人交易|跨國稅務|國際租稅|全球最低稅負|關稅|扣繳稅|常設機構|供應鏈|營運據點|營運|據點|年報|財報|永續報告|tax risk|tax governance|tax policy|tax strategy|tax transparency|income tax expense|income tax|deferred tax|tax audit|tax investigation|tax probe|tax row|tax notice|tax notices|tax assessment|tax demand|property tax|land tax|tax penalty|tax dispute|tax litigation|tax settlement|tax incentives|transfer pricing|cross-border tax|international tax|global minimum tax|pillar two|withholding tax|permanent establishment|customs duty|tariff|supply chain|operations|locations|annual report|financial statement|financial statements|sustainability report|integrated report)$", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"(跨國|全球|國際|海外|所有|全部|全體|旗下所有|旗下|相關|cross-border|global|international|overseas|worldwide|recent|latest)$", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"(及其|以及|和|與)?(子公司|主要子公司|母公司|關係企業|關聯企業|集團|旗下公司|subsidiaries|subsidiary|affiliates|affiliate companies|parent company)$", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"(股份有限公司|有限公司|股份有限|公司|集團|控股|holding company|holdings|corporation|corp\.?|inc\.?|ltd\.?|limited)$", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"(及其|以及|和|與)$", "", cleaned, flags=re.IGNORECASE).strip()
            if cleaned == previous:
                break
        cleaned = cleaned.strip(" -_，,。")
        if cleaned in {"母", "子"}:
            return ""
        return cleaned

    def _expand_known_company_aliases(self, term: str) -> List[str]:
        aliases = []
        lowered = term.lower()
        for key, values in self.COMPANY_ALIAS_MAP.items():
            if key.lower() in lowered:
                aliases.extend(values)
        return aliases

    def _expand_generic_company_aliases(self, term: str) -> List[str]:
        cleaned = self._clean_entity_alias(term)
        if not cleaned or self._is_low_value_alias(cleaned):
            return []

        aliases = [cleaned]
        has_cjk = bool(re.search(r"[\u4e00-\u9fff]", cleaned))
        if has_cjk:
            aliases.extend([
                f"{cleaned}公司",
                f"{cleaned}集團",
                f"{cleaned}股份有限公司",
                f"{cleaned}子公司",
                f"{cleaned}關係企業",
            ])
        else:
            aliases.extend([
                f"{cleaned} Inc",
                f"{cleaned} Corporation",
                f"{cleaned} Corp",
                f"{cleaned} Group",
                f"{cleaned} Holdings",
                f"{cleaned} subsidiaries",
                f"{cleaned} affiliates",
            ])
        return aliases

    def _split_compact_topic_query(self, term: str) -> List[str]:
        expansions = []
        compact_topics = [
            "稅務稽查",
            "稅務調查",
            "稅務查核",
            "稅務裁罰",
            "稅務罰鍰",
            "稅務爭議",
            "稅務及用地",
            "用地調查",
            "查稅",
            "查稅結果",
            "虛假計稅",
            "補稅",
            "欠稅",
            "漏稅",
            "tax audit",
            "tax investigation",
            "tax probe",
            "tax row",
            "tax notice",
            "tax assessment",
            "property tax",
            "land tax",
            "tax penalty",
            "tax dispute",
            "tax litigation",
            "稅務風險",
            "稅務治理",
            "所得稅",
            "營所稅",
            "移轉訂價",
            "關係人交易",
            "年報",
            "財報",
            "永續報告",
            "tax risk",
            "tax governance",
            "tax policy",
            "tax strategy",
            "tax transparency",
            "income tax",
            "income tax expense",
            "deferred tax",
            "tax audit",
            "tax incentives",
            "transfer pricing",
            "international tax",
            "cross-border tax",
            "global minimum tax",
            "pillar two",
            "beps",
            "withholding tax",
            "customs duty",
            "tariff",
            "cfc",
            "annual report",
            "financial statement",
            "financial statements",
            "sustainability report",
            "integrated report",
            "subsidiaries",
            "subsidiary",
            "affiliates",
            "affiliate",
            "related party transactions",
            "稅務",
            "風險",
        ]
        lowered = term.lower()
        for topic in compact_topics:
            topic_lower = topic.lower()
            if topic_lower not in lowered or lowered == topic_lower:
                continue
            entity = re.sub(re.escape(topic), "", term, flags=re.IGNORECASE).strip()
            entity = self._clean_entity_alias(entity)
            if entity:
                expansions.append(entity)
                expansions.extend(self._expand_known_company_aliases(entity))
                expansions.extend(self._expand_generic_company_aliases(entity))
            expansions.append(topic)
            if topic in {"稅務稽查", "稅務調查", "稅務查核", "稅務裁罰", "稅務罰鍰", "稅務爭議", "補稅", "欠稅", "漏稅", "稅務風險", "稅務治理", "所得稅", "移轉訂價", "關係人交易", "tax audit", "tax investigation", "tax probe", "tax penalty", "tax dispute", "tax litigation", "tax risk", "tax governance", "income tax", "transfer pricing"}:
                break
        return expansions

    def _is_low_value_alias(self, alias: str) -> bool:
        lowered = alias.lower().strip()
        if not lowered:
            return True
        low_value_terms = {
            "風險",
            "高風險",
            "稽查",
            "調查",
            "查核",
            "裁罰",
            "罰鍰",
            "補稅",
            "欠稅",
            "漏稅",
            "爭議",
            "相關",
            "來源",
            "各來源",
            "全部來源",
            "所有來源",
            "個月內各來源",
            "個月內",
            "母",
            "母公司",
            "子公司",
            "主要子公司",
            "關係企業",
            "關聯企業",
            "集團",
            "旗下公司",
            "公司",
            "month",
            "months",
            "source",
            "sources",
            "global",
            "international",
            "cross-border",
            "overseas",
            "worldwide",
            "recent",
            "latest",
            "annual",
            "report",
            "reports",
            "financial",
            "statement",
            "statements",
            "sustainability",
            "integrated",
            "policy",
            "strategy",
            "transparency",
            "governance",
            "minimum",
            "effective",
            "rate",
            "expense",
            "assets",
            "liabilities",
            "obligation",
            "filing",
            "transfer",
            "pricing",
            "related",
            "party",
            "parties",
            "transaction",
            "transactions",
            "compliance",
            "management",
            "deferred",
            "incentives",
            "audit",
            "risk",
            "risks",
            "pillar",
            "two",
            "beps",
            "vat",
            "gst",
            "cfc",
            "tax",
            "withholding",
            "customs",
            "tariff",
            "penalty",
            "fine",
            "dispute",
            "investigation",
            "probe",
            "notice",
            "notices",
            "assessment",
            "demand",
            "row",
            "property",
            "land",
            "settlement",
            "reassessment",
            "anti-dumping",
            "countervailing",
            "duty",
            "supply",
            "chain",
            "parent",
            "parent company",
            "subsidiary",
            "subsidiaries",
            "affiliate",
            "affiliates",
            "group",
            "company",
        }
        low_value_terms.update(phrase.lower() for phrase in self.TAX_KEYPHRASES)
        low_value_terms.update(phrase.lower() for phrase in self.TAX_RISK_EVENT_TOPICS)
        low_value_terms.update(phrase.lower() for phrase in self.COMPANY_RESEARCH_TOPICS)
        low_value_terms.update(phrase.lower() for phrase in self.SUBSIDIARY_RESEARCH_TOPICS)
        if lowered in low_value_terms:
            return True
        if "個月" in lowered and "來源" in lowered:
            return True
        if re.fullmatch(r"(母|子)(公司|集團|股份有限公司|子公司|關係企業)?", lowered):
            return True
        if re.fullmatch(r"\d+[dmy]?", lowered):
            return True
        return False

    def _expand_company_suffix_aliases(self, term: str) -> List[str]:
        suffix_map = {
            "holding": ["group", "subsidiary", "affiliate"],
            "holdings": ["group", "subsidiary", "affiliate"],
            "group": ["holding", "holdings", "subsidiary"],
            "corp": ["corporation", "group"],
            "corporation": ["corp", "group"],
            "co": ["company", "group"],
            "company": ["co", "group"],
        }
        parts = term.split()
        if not parts:
            return []
        lowered_parts = [part.lower() for part in parts]
        expansions = []
        for index, part in enumerate(lowered_parts):
            if part not in suffix_map:
                continue
            for replacement in suffix_map[part]:
                new_parts = parts[:]
                new_parts[index] = replacement
                expansions.append(" ".join(new_parts))
        return expansions

    def _expand_group_entity_aliases(self, term: str) -> List[str]:
        replacements = [
            ("控股", ["集團", "子公司", "關係企業"]),
            ("集团", ["控股", "子公司", "关联企业"]),
            ("集團", ["控股", "子公司", "關係企業"]),
            ("子公司", ["集團", "控股", "母公司"]),
            ("母公司", ["子公司", "集團", "控股"]),
            ("關係企業", ["集團", "子公司"]),
            ("affiliate", ["group", "subsidiary"]),
            ("subsidiary", ["group", "affiliate", "holding"]),
            ("parent company", ["subsidiary", "group", "holding"]),
        ]
        expansions = []
        lowered = term.lower()
        for source, targets in replacements:
            source_lower = source.lower()
            if source_lower in lowered:
                for target in targets:
                    if source in term:
                        expanded = term.replace(source, target)
                    else:
                        expanded = re.sub(source_lower, target, lowered, flags=re.IGNORECASE)
                    cleaned = self._clean_entity_alias(expanded)
                    if cleaned:
                        expansions.append(cleaned)
        return expansions

    def _build_query_variants(self, keywords: List[str], user_prompt: str = None) -> List[str]:
        joined_keywords = " ".join(keyword.strip() for keyword in keywords if keyword.strip()).strip()
        variants = [joined_keywords]
        aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)

        for alias in aliases[:8]:
            variants.append(f"\"{alias}\" annual report tax")
        for alias in aliases[:8]:
            variants.append(f"\"{alias}\" tax policy")
            variants.append(f"\"{alias}\" financial statements income tax")
            variants.append(f"\"{alias}\" subsidiaries tax")

        for alias in aliases[:6]:
            for topic in self.COMPANY_RESEARCH_TOPICS[:12]:
                variants.append(f"\"{alias}\" {topic}")
            for topic in self.SUBSIDIARY_RESEARCH_TOPICS[:8]:
                variants.append(f"\"{alias}\" {topic}")
            variants.append(f"\"{alias}\" annual report tax")
            variants.append(f"\"{alias}\" sustainability report tax")
            variants.append(f"\"{alias}\" subsidiaries tax")
            variants.append(f"\"{alias}\" related party transactions tax")
            variants.append(f"\"{alias}\" 年報 稅務")
            variants.append(f"\"{alias}\" 子公司 稅務")
            variants.append(f"\"{alias}\" 關係企業 所得稅")

        short_keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
        if len(short_keywords) >= 2:
            variants.append(" ".join(short_keywords[:2]))
            variants.append(" ".join(short_keywords[:3]))

        prompt_terms = [
            term for term in re.findall(r"[a-zA-Z0-9_-]{3,}|[\u4e00-\u9fff]{2,}", user_prompt or "")
            if not self._is_low_value_alias(term)
        ]
        if prompt_terms:
            variants.append(f"{joined_keywords} {' '.join(prompt_terms[:5])}")

        seed_topics = [
            "tax update",
            "tax reform",
            "compliance",
            "penalty",
            "filing obligation",
            "effective date",
            "draft regulation",
            "tax audit",
            "tax investigation",
            "tax penalty",
            "transfer pricing audit",
            "tariff impact",
            "稅務稽查",
            "稅務裁罰",
            "補稅",
            "關稅 衝擊",
        ]
        for topic in seed_topics:
            if topic not in joined_keywords.lower():
                variants.append(f"{joined_keywords} {topic}".strip())

        normalized = []
        seen = set()
        for variant in variants:
            cleaned = " ".join(variant.split()).strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized[:36]

    def _build_ai_query_variants(
        self,
        keywords: List[str],
        user_prompt: str = None,
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        enabled: bool = True
    ) -> List[str]:
        if not enabled:
            return []

        prompt = f"""
You are a search strategist for tax and regulatory monitoring.
Given the user's keywords and intent, generate related search queries that may find relevant results
even when the exact original wording is not used.

Return JSON only:
{{
  "queries": [
    "query 1",
    "query 2",
    "query 3"
  ]
}}

Original keywords: {keywords}
User intent: {user_prompt or ""}

Requirements:
- include semantic alternatives
- include regulatory / filing / compliance synonyms
- if the keywords include a company, infer likely legal names, English names, stock names, abbreviations, group names, and subsidiary wording
- include annual report, sustainability report, financial statement, tax governance, income tax, transfer pricing, related party transactions, subsidiaries, affiliates, group structure
- keep each query concise
- do not include explanations
"""
        data = self.llm_service.generate_json(
            prompt=prompt,
            schema_hint={"queries": []},
            provider=provider,
            model_name=model_name
        )
        queries = data.get("queries", [])
        if not isinstance(queries, list):
            return []
        cleaned = []
        seen = set()
        for query in queries:
            if not isinstance(query, str):
                continue
            normalized = " ".join(query.split()).strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(normalized)
        return cleaned[:8]

    def _merge_query_variants(self, keywords: List[str], user_prompt: str, ai_variants: List[str]) -> List[str]:
        base_variants = self._build_query_variants(keywords=keywords, user_prompt=user_prompt)
        combined = []
        seen = set()

        prioritized = []
        if base_variants:
            prioritized.append(base_variants[0])
        prioritized.extend(ai_variants[:6])
        prioritized.extend(base_variants[1:])
        prioritized.extend(ai_variants[6:])

        for variant in prioritized:
            lowered = variant.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            combined.append(variant)
        return combined[:36]

    def _search_bing_news_rss(self, query: str, window: Dict[str, datetime], max_results: int) -> List[Dict]:
        when_clause = self._build_google_news_when(window)
        full_query = f"{query} {when_clause}".strip()
        url = f"https://www.bing.com/news/search?q={quote_plus(full_query)}&format=rss"
        return self._fetch_google_news_feed(url=url, max_results=max_results, source_name="bing_news_rss")

    def _search_google_news_archive(self, query: str, max_results: int) -> List[Dict]:
        archive_locales = [
            {"hl": "zh-TW", "gl": "TW", "ceid": "TW:zh-Hant"},
            {"hl": "zh-HK", "gl": "HK", "ceid": "HK:zh-Hant"},
            {"hl": "en-US", "gl": "US", "ceid": "US:en"},
            {"hl": "en-GB", "gl": "GB", "ceid": "GB:en"},
        ]
        merged = []
        seen_urls = set()
        for locale in archive_locales:
            url = (
                "https://news.google.com/rss/search"
                f"?q={quote_plus(query)}"
                f"&hl={locale['hl']}&gl={locale['gl']}&ceid={locale['ceid']}"
            )
            for item in self._fetch_google_news_feed(
                url=url,
                max_results=max_results,
                source_name="google_news_archive"
            ):
                item["is_historical_context"] = True
                self._append_unique_result(merged, seen_urls, item)
            if len(merged) >= max_results:
                break
        return merged[:max_results]

    def _search_bing_web(self, query: str, max_results: int) -> List[Dict]:
        url = f"https://www.bing.com/search?q={quote_plus(query)}&setlang=zh-TW&cc=TW"
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=self.SEARCH_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for result in soup.select("li.b_algo"):
            link = result.select_one("h2 a")
            if not link:
                continue
            href = self._normalize_result_url(link.get("href") or "")
            title = link.get_text(" ", strip=True)
            snippet_node = result.select_one(".b_caption p") or result.select_one("p")
            results.append({
                "title": title,
                "url": href,
                "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
                "source": "bing_web",
                "published_at": None,
                "relevance_score": 0.0
            })
            if len(results) >= max_results:
                break
        return results

    def _search_bing_pdf(self, query: str, max_results: int) -> List[Dict]:
        return self._search_bing_web(f"{query} filetype:pdf", max_results)

    def _search_duckduckgo_html(self, query: str, max_results: int) -> List[Dict]:
        url = "https://html.duckduckgo.com/html/"
        response = requests.post(
            url,
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=self.SEARCH_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for result in soup.select(".result"):
            link = result.select_one(".result__title a")
            snippet = result.select_one(".result__snippet")
            if not link:
                continue
            href = self._normalize_result_url(link.get("href") or "")
            title = link.get_text(" ", strip=True)
            results.append({
                "title": title,
                "url": href,
                "snippet": snippet.get_text(" ", strip=True) if snippet else "",
                "source": "duckduckgo_html",
                "published_at": None,
                "relevance_score": 0.0
            })
            if len(results) >= max_results:
                break
        return results

    def _search_duckduckgo_pdf(self, query: str, max_results: int) -> List[Dict]:
        return self._search_duckduckgo_html(f"{query} filetype:pdf", max_results)

    def _safe_search_call(self, search_func, *args) -> List[Dict]:
        try:
            return search_func(*args)
        except Exception:
            return []

    def _append_unique_result(self, merged: List[Dict], seen_urls: set, item: Dict):
        normalized_url = self._normalize_result_url(item.get("url") or "").strip()
        normalized_key = normalized_url.lower()
        if not normalized_key or normalized_key in seen_urls or self._should_skip_result_url(normalized_url):
            return
        item["url"] = normalized_url
        seen_urls.add(normalized_key)
        merged.append(item)

    def _normalize_result_url(self, href: str) -> str:
        href = (href or "").strip()
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = urljoin("https://duckduckgo.com", href)

        parsed = urlparse(href)
        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg")
            if target:
                return unquote(target[0])
        if "bing.com" in parsed.netloc and parsed.path.startswith("/ck/"):
            target = parse_qs(parsed.query).get("u")
            if target:
                encoded = target[0]
                if encoded.startswith("a1"):
                    encoded = encoded[2:]
                try:
                    padding = "=" * (-len(encoded) % 4)
                    return base64.urlsafe_b64decode((encoded + padding).encode("ascii")).decode("utf-8")
                except Exception:
                    return unquote(target[0])
        return href

    def _should_skip_result_url(self, url: str) -> bool:
        domain = self._extract_domain(url)
        return domain in self.LOW_SIGNAL_DOMAINS

    def _fetch_google_news_feed(self, url: str, max_results: int, source_name: str) -> List[Dict]:
        response = requests.get(url, timeout=self.SEARCH_TIMEOUT_SECONDS, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        root = ET.fromstring(response.text)
        items = []
        for item in root.findall(".//item"):
            pub_date = item.findtext("pubDate")
            normalized_date = None
            if pub_date:
                try:
                    normalized_date = parsedate_to_datetime(pub_date).isoformat()
                except Exception:
                    normalized_date = pub_date
            items.append({
                "title": item.findtext("title", default=""),
                "url": item.findtext("link", default=""),
                "snippet": item.findtext("description", default=""),
                "source": source_name,
                "published_at": normalized_date,
                "relevance_score": 0.0
            })
            if len(items) >= max_results:
                break
        return items

    def _rank_results(self, results: List[Dict], keywords: List[str], user_prompt: str = None) -> List[Dict]:
        prompt_terms = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_-]{2,}", (user_prompt or "").lower())
        entity_aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        event_intent = self._has_tax_event_intent(keywords=keywords, user_prompt=user_prompt)

        for result in results:
            haystack = " ".join([
                result.get("title", ""),
                result.get("snippet", "")
            ]).lower()
            url = result.get("url", "")
            domain = self._extract_domain(url)

            keyword_hits = sum(2.5 for keyword in keywords if keyword.lower() in haystack)
            prompt_hits = sum(1 for term in prompt_terms if term in haystack)
            tax_phrase_hits = sum(0.6 for phrase in self.TAX_KEYPHRASES if phrase.lower() in haystack)
            tax_event_hits = sum(
                1.2
                for phrase in self.TAX_RISK_EVENT_TOPICS
                if phrase.lower() in haystack or phrase.lower() in url.lower()
            )
            subsidiary_hits = sum(
                0.9
                for phrase in self.SUBSIDIARY_RESEARCH_TOPICS
                if phrase.lower() in haystack or phrase.lower() in url.lower()
            )
            alias_hits = sum(1.5 for alias in entity_aliases if alias.lower() in haystack or alias.lower() in url.lower())
            domain_alias_bonus = 1.4 if self._domain_matches_alias(domain, entity_aliases) else 0.0
            freshness_bonus = 0.5 if result.get("published_at") else 0.0
            official_bonus = 2.2 if self._is_official_tax_domain(domain) else 0.0
            disclosure_bonus = 1.6 if self._is_disclosure_domain(domain, entity_aliases) else 0.0
            tax_news_bonus = 1.1 if self._is_tax_news_domain(domain) and (alias_hits > 0 or domain_alias_bonus > 0 or tax_event_hits > 0) else 0.0
            event_news_bonus = 1.0 if "news" in (result.get("source") or "").lower() and tax_event_hits > 0 else 0.0
            pdf_bonus = 1.0 if self._looks_like_pdf(result) else 0.0
            title_bonus = 0.8 if any(keyword.lower() in (result.get("title", "").lower()) for keyword in keywords) else 0.0
            source_bonus = 0.4 if result.get("source", "").startswith("google_news_rss") else 0.0
            source_bonus += 0.3 if result.get("source") == "bing_news_rss" else 0.0
            source_bonus += 0.2 if result.get("source") == "bing_web" else 0.0
            source_bonus += 1.4 if result.get("source") == "official_seed" else 0.0
            source_bonus += 1.0 if result.get("source") == "official_domain_seed" else 0.0
            source_bonus += 1.0 if result.get("source") == "reference_seed" else 0.0
            topical_signal = prompt_hits + tax_phrase_hits + tax_event_hits + subsidiary_hits + official_bonus + disclosure_bonus + tax_news_bonus + pdf_bonus
            weak_topic_penalty = 2.6 if alias_hits > 0 and topical_signal < 1.0 else 0.0
            social_penalty = 1.2 if domain in {"www.linkedin.com", "linkedin.com", "www.pressreader.com", "pressreader.com"} else 0.0
            has_company_focus = bool(entity_aliases)
            generic_reference_penalty = 4.0 if result.get("source") == "reference_seed" and alias_hits == 0 else 0.0
            unrelated_company_penalty = (
                3.2
                if has_company_focus
                and alias_hits == 0
                and domain_alias_bonus == 0
                and result.get("source") != "reference_seed"
                and not self._is_official_tax_domain(domain)
                else 0.0
            )
            event_document_penalty = (
                2.0
                if event_intent
                and tax_event_hits == 0
                and self._looks_like_pdf(result)
                and result.get("source") != "official_seed"
                else 0.0
            )

            result["domain"] = domain
            result["result_type"] = self._infer_result_type(result)
            result["match_reasons"] = self._build_match_reasons(
                result=result,
                keywords=keywords,
                prompt_terms=prompt_terms,
                entity_aliases=entity_aliases,
                official_bonus=official_bonus,
                disclosure_bonus=disclosure_bonus,
                pdf_bonus=pdf_bonus
            )
            result["relevance_score"] = round(
                keyword_hits
                + prompt_hits
                + tax_phrase_hits
                + tax_event_hits
                + subsidiary_hits
                + alias_hits
                + domain_alias_bonus
                + freshness_bonus
                + official_bonus
                + disclosure_bonus
                + tax_news_bonus
                + event_news_bonus
                + pdf_bonus
                + title_bonus
                + source_bonus
                - weak_topic_penalty
                - social_penalty
                - generic_reference_penalty
                - unrelated_company_penalty
                - event_document_penalty,
                2
            )
            if result.get("source") == "reference_seed" and alias_hits == 0 and domain_alias_bonus == 0 and has_company_focus:
                result["relevance_score"] = min(result["relevance_score"], 4.2)
            if result.get("source") == "official_domain_seed":
                result["relevance_score"] = min(result["relevance_score"], 5.8)
            if event_intent and result.get("source") == "official_seed" and tax_event_hits == 0:
                result["relevance_score"] = min(result["relevance_score"], 6.4)
            if event_intent and result.get("source") == "official_domain_seed" and tax_event_hits == 0:
                result["relevance_score"] = min(result["relevance_score"], 4.8)

        return sorted(results, key=lambda item: item["relevance_score"], reverse=True)

    def _normalize_keywords(self, keywords: List[str]) -> List[str]:
        normalized = []
        seen = set()
        for keyword in keywords or []:
            parts = re.split(r"[\n,，;；|]+", str(keyword))
            for part in parts:
                cleaned = " ".join(part.split()).strip()
                if not cleaned:
                    continue
                lowered = cleaned.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                normalized.append(cleaned)
        return normalized

    def _build_match_reasons(
        self,
        result: Dict,
        keywords: List[str],
        prompt_terms: List[str],
        entity_aliases: List[str],
        official_bonus: float,
        disclosure_bonus: float,
        pdf_bonus: float
    ) -> List[str]:
        haystack = " ".join([
            result.get("title", ""),
            result.get("snippet", "")
        ]).lower()
        reasons = []

        matched_keywords = [keyword for keyword in keywords if keyword.lower() in haystack][:3]
        if matched_keywords:
            reasons.append(f"命中關鍵字：{', '.join(matched_keywords)}")

        matched_prompt_terms = [term for term in prompt_terms if term in haystack][:3]
        if matched_prompt_terms:
            reasons.append(f"符合補充需求：{', '.join(matched_prompt_terms)}")

        matched_aliases = [alias for alias in entity_aliases if alias.lower() in haystack or alias.lower() in (result.get('url', '').lower())][:2]
        if matched_aliases:
            reasons.append(f"抓到主體別名：{', '.join(matched_aliases)}")

        if official_bonus > 0:
            reasons.append("官方 / 顧問 / 稅務站點加權")

        if disclosure_bonus > 0:
            reasons.append("年報 / 財報 / 公開資訊來源加權")

        matched_group_terms = [
            term
            for term in [
                "subsidiaries",
                "subsidiary",
                "related party",
                "affiliate",
                "group structure",
                "consolidated financial statements",
                "子公司",
                "關係企業",
                "集團架構",
                "合併財務報表",
                "轉投資",
            ]
            if term.lower() in haystack
        ][:3]
        if matched_group_terms:
            reasons.append(f"命中集團 / 子公司語境：{', '.join(matched_group_terms)}")

        matched_event_terms = [
            term
            for term in self.TAX_RISK_EVENT_TOPICS
            if term.lower() in haystack or term.lower() in (result.get("url", "").lower())
        ][:3]
        if matched_event_terms:
            reasons.append(f"命中稅務事件線索：{', '.join(matched_event_terms)}")

        if pdf_bonus > 0:
            reasons.append("PDF / 文件型資料優先")

        if result.get("published_at"):
            reasons.append("有可用發布時間")

        if result.get("is_historical_context"):
            reasons.append("歷史稅務事件脈絡")

        if not reasons:
            reasons.append("語意相近且整體相關")

        return reasons[:4]

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            return (parsed.netloc or "").lower()
        except Exception:
            return ""

    def _is_official_tax_domain(self, domain: str) -> bool:
        return any(domain.endswith(official_domain) for official_domain in self.OFFICIAL_TAX_DOMAINS)

    def _is_disclosure_domain(self, domain: str, aliases: List[str]) -> bool:
        disclosure_domains = self._disclosure_domains_for_aliases(aliases)
        return any(domain.endswith(disclosure_domain) for disclosure_domain in disclosure_domains)

    def _is_tax_news_domain(self, domain: str) -> bool:
        return any(domain.endswith(news_domain) for news_domain in self.TAX_NEWS_DOMAINS)

    def _has_tax_event_intent(self, keywords: List[str], user_prompt: str = None) -> bool:
        text = " ".join(keywords + [user_prompt or ""]).lower()
        return any(topic.lower() in text for topic in self.TAX_RISK_EVENT_TOPICS)

    def _domain_matches_alias(self, domain: str, aliases: List[str]) -> bool:
        compact_domain = re.sub(r"[^a-z0-9]", "", domain.lower())
        for alias in aliases:
            compact_alias = re.sub(r"[^a-z0-9]", "", alias.lower())
            if len(compact_alias) < 4:
                continue
            if compact_alias in compact_domain:
                return True
        return False

    def _looks_like_pdf(self, result: Dict) -> bool:
        url = (result.get("url") or "").lower()
        snippet = (result.get("snippet") or "").lower()
        title = (result.get("title") or "").lower()
        return ".pdf" in url or "pdf" in snippet or "pdf" in title

    def _infer_result_type(self, result: Dict) -> str:
        if self._looks_like_pdf(result):
            return "pdf"
        source = (result.get("source") or "").lower()
        if "news" in source:
            return "news"
        return "web"

    def _resolve_date_window(self, date_range: str, start_date: str = None, end_date: str = None) -> Dict[str, datetime]:
        now = datetime.utcnow()
        mapping = {
            "7d": timedelta(days=7),
            "1m": timedelta(days=30),
            "3m": timedelta(days=90),
            "6m": timedelta(days=180),
            "1y": timedelta(days=365)
        }

        if date_range == "custom" and start_date and end_date:
            return {
                "start": datetime.fromisoformat(start_date),
                "end": datetime.fromisoformat(end_date)
            }

        delta = mapping.get(date_range, timedelta(days=30))
        return {"start": now - delta, "end": now}

    def _build_google_news_when(self, window: Dict[str, datetime]) -> str:
        start = window["start"]
        end = window["end"]
        delta_days = max((end - start).days, 1)
        if delta_days <= 7:
            return "when:7d"
        if delta_days <= 30:
            return "when:30d"
        if delta_days <= 90:
            return "when:90d"
        if delta_days <= 180:
            return "when:180d"
        return "when:365d"

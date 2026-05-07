from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import base64
import itertools
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:
    Retry = None

from services.llm_service import LLMService


class SearchService:
    SEARCH_TIMEOUT_SECONDS = 8
    DEEP_FETCH_TIMEOUT_SECONDS = 12
    CACHE_TTL_SECONDS = 600
    CACHE_MAX_ENTRIES = 256
    POLITE_UA_POOL = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    )
    SEC_USER_AGENT = "Tax Monitor Research Bot acc.capstone.115@gmail.com"

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
        "bdo.global",
        "grantthornton.global",
        "ibfd.org",
        "taxfoundation.org",
        "tax.thomsonreuters.com",
        "internationaltaxreview.com",
        "irs.gov",
        "treasury.gov",
        "ec.europa.eu",
        "eur-lex.europa.eu",
        "taxation-customs.ec.europa.eu",
        "gov.uk",
        "hmrc.gov.uk",
        "bundesfinanzministerium.de",
        "impots.gouv.fr",
        "agenziaentrate.gov.it",
        "minfin.gov.ua",
        "skatteverket.se",
        "skatteetaten.no",
        "mof.gov.tw",
        "dot.gov.tw",
        "moj.gov.tw",
        "law.moj.gov.tw",
        "ntbt.gov.tw",
        "ntbk.gov.tw",
        "ntbsa.gov.tw",
        "tax.gov.tw",
        "fsc.gov.tw",
        "nta.go.jp",
        "mof.go.jp",
        "nts.go.kr",
        "moef.go.kr",
        "iras.gov.sg",
        "ird.gov.hk",
        "chinatax.gov.cn",
        "mof.gov.cn",
        "incometax.gov.in",
        "gst.gov.in",
        "ato.gov.au",
        "ird.govt.nz",
        "sars.gov.za",
        "canada.ca",
        "sat.gob.mx",
        "rfb.gov.br",
        "afip.gob.ar",
    ]

    DISCLOSURE_DOMAINS = [
        "twse.com.tw",
        "mops.twse.com.tw",
        "mopsov.twse.com.tw",
        "tpex.org.tw",
        "annualreports.com",
        "marketscreener.com",
        "sec.gov",
        "efts.sec.gov",
        "reuters.com",
        "stockanalysis.com",
        "companiesmarketcap.com",
        "jpx.co.jp",
        "release.tdnet.info",
        "disclosure2.edinet-fsa.go.jp",
        "edinet-fsa.go.jp",
        "dart.fss.or.kr",
        "hkexnews.hk",
        "krx.co.kr",
        "sgx.com",
        "asx.com.au",
        "bseindia.com",
        "nseindia.com",
        "sse.com.cn",
        "szse.cn",
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

    AUDIT_SAMPLING_TERMS = [
        "tax audit selection",
        "tax audit case selection",
        "audit case selection criteria",
        "risk-based audit selection",
        "risk-based audit",
        "tax authority sampling",
        "audit sampling risk",
        "high-risk taxpayer list",
        "tax compliance risk scoring",
        "transfer pricing case selection",
        "controlled transaction selection",
        "MAP request",
        "mutual agreement procedure",
        "advance pricing arrangement",
        "advance ruling request",
        "private letter ruling",
        "tax demand letter",
        "deficiency notice",
        "notice of audit",
        "tax reassessment notice",
        "back tax demand",
        "稅務查核抽樣",
        "稅務抽核",
        "選案查核",
        "風險選案",
        "重點查核",
        "查核重點",
        "查核選案",
        "高風險納稅義務人",
        "高風險納稅人",
        "高風險案件",
        "稅務風險評估",
        "稅務風險導向查核",
        "移轉訂價選案",
        "受控交易選案",
        "預先核釋",
        "預先訂價協議",
        "稅務裁罰書",
        "繳款書",
        "補徵稅款",
        "補徵核定通知書",
        "滯納金",
        "罰鍰",
        "申請相互協議",
        "税務調査対象",
        "抽出調査",
        "重点調査",
        "リスクベース調査",
        "更正処分",
        "国税庁 査察",
        "세무조사 선정",
        "고위험 납세자",
        "위험기반 세무조사",
        "추징세액",
        "신고불성실 가산세",
        "稅務稽查抽查",
        "随机抽查",
        "重点稽查",
    ]

    TAX_AUDIT_THESAURUS = {
        "audit": [
            "audit", "tax audit", "audit examination", "review", "examination",
            "investigation", "tax investigation", "probe", "tax probe", "inspection",
            "查核", "稅務查核", "稽查", "稅務稽查", "調查", "稅務調查",
            "查稅", "国税庁 査察", "税務調査", "세무조사", "审查", "稽查抽查",
        ],
        "sampling": [
            "audit sampling", "sample selection", "case selection", "risk-based selection",
            "risk-based audit", "high-risk taxpayer", "compliance risk scoring",
            "抽核", "選案", "選案查核", "風險選案", "重點查核", "高風險納稅人",
            "抽出調査", "リスクベース調査", "고위험 납세자", "위험기반 세무조사",
            "随机抽查", "重点稽查",
        ],
        "penalty": [
            "penalty", "fine", "surcharge", "back tax", "additional tax",
            "deficiency notice", "demand letter", "reassessment notice",
            "罰鍰", "罰款", "滯納金", "滯報金", "怠報金", "補徵稅款",
            "補稅", "繳款書", "稅務裁罰書", "更正処分", "추징세액",
            "신고불성실 가산세", "罰則", "加算税",
        ],
        "transfer_pricing": [
            "transfer pricing", "TP audit", "arm's length principle", "comparables",
            "intercompany transactions", "controlled transactions", "BEPS Action 8",
            "BEPS Action 9", "BEPS Action 10", "OECD transfer pricing guidelines",
            "country-by-country report", "CbC report", "master file", "local file",
            "移轉訂價", "移轉訂價查核", "受控交易", "關聯交易",
            "国別報告書", "ローカルファイル", "マスターファイル",
            "이전가격", "특수관계자 거래",
        ],
        "pillar_two": [
            "Pillar Two", "Pillar 2", "GloBE", "global minimum tax", "GMT",
            "QDMTT", "qualified domestic minimum top-up tax", "IIR", "income inclusion rule",
            "UTPR", "undertaxed payments rule", "GILTI",
            "全球最低稅負", "支柱二", "合格國內最低補充稅",
            "グローバルミニマム課税", "글로벌 최저한세",
        ],
        "cfc": [
            "CFC", "controlled foreign company", "controlled foreign corporation",
            "subpart F", "anti-deferral rules",
            "受控外國公司", "CFC 制度", "受控外國企業所得",
            "外国子会社合算税制", "타국 자회사 합산과세",
        ],
        "permanent_establishment": [
            "permanent establishment", "PE risk", "PE assessment",
            "fixed place of business", "agency PE", "service PE",
            "常設機構", "PE 風險",
            "恒久的施設", "고정사업장",
        ],
        "withholding_tax": [
            "withholding tax", "WHT", "withholding obligation",
            "扣繳稅", "扣繳義務", "預扣稅款",
            "源泉徴収税", "원천징수",
        ],
        "tariff": [
            "tariff", "customs duty", "import duty", "export duty",
            "anti-dumping", "countervailing", "Section 301", "Section 232",
            "關稅", "進口稅", "海關估價", "反傾銷稅", "反補貼稅",
            "関税", "관세",
        ],
        "vat_gst": [
            "VAT", "value added tax", "GST", "goods and services tax",
            "consumption tax", "sales tax", "indirect tax",
            "加值稅", "加值營業稅", "營業稅", "消費稅",
            "消費税", "부가가치세",
        ],
    }

    JURISDICTION_PROFILE = {
        "tw": {
            "languages": ["zh-TW", "en"],
            "audit_terms": ["國稅局查核", "選案查核", "查核重點", "罰鍰", "補徵稅款"],
            "authority_aliases": ["國稅局", "財政部", "MOF", "MOJ"],
            "filing_terms": ["年度結算申報", "暫繳申報", "扣繳憑單"],
        },
        "jp": {
            "languages": ["ja", "en"],
            "audit_terms": ["税務調査", "国税庁 査察", "更正処分", "加算税"],
            "authority_aliases": ["国税庁", "NTA", "国税局", "税務署"],
            "filing_terms": ["法人税申告", "確定申告", "源泉徴収"],
        },
        "kr": {
            "languages": ["ko", "en"],
            "audit_terms": ["세무조사", "추징세액", "신고불성실 가산세"],
            "authority_aliases": ["국세청", "NTS", "세무서"],
            "filing_terms": ["법인세 신고", "원천징수"],
        },
        "cn": {
            "languages": ["zh-CN", "en"],
            "audit_terms": ["税务稽查", "税务检查", "重点稽查", "随机抽查", "补缴税款"],
            "authority_aliases": ["国家税务总局", "税务局", "SAT"],
            "filing_terms": ["企业所得税汇算清缴", "增值税申报"],
        },
        "hk": {
            "languages": ["en", "zh-HK"],
            "audit_terms": ["IRD audit", "field audit", "investigation"],
            "authority_aliases": ["Inland Revenue Department", "IRD", "稅務局"],
            "filing_terms": ["profits tax return", "BIR51"],
        },
        "sg": {
            "languages": ["en"],
            "audit_terms": ["IRAS audit", "tax investigation", "risk-based audit"],
            "authority_aliases": ["IRAS", "Inland Revenue Authority of Singapore"],
            "filing_terms": ["corporate income tax filing", "Form C-S"],
        },
        "us": {
            "languages": ["en"],
            "audit_terms": ["IRS audit", "examination", "deficiency notice", "Notice of Deficiency", "CDP hearing"],
            "authority_aliases": ["IRS", "Internal Revenue Service", "Treasury"],
            "filing_terms": ["10-K", "20-F", "Form 5471", "Form 5472", "Schedule UTP"],
        },
        "eu": {
            "languages": ["en"],
            "audit_terms": ["DAC6 disclosure", "ATAD", "anti-tax avoidance directive"],
            "authority_aliases": ["European Commission", "DG TAXUD"],
            "filing_terms": ["DAC6 reporting", "CESOP"],
        },
        "in": {
            "languages": ["en"],
            "audit_terms": ["GST audit", "income tax scrutiny", "GAAR", "Vivad se Vishwas"],
            "authority_aliases": ["CBDT", "CBIC", "Income Tax Department"],
            "filing_terms": ["Form 3CD", "Form 3CEB", "Tax Audit Report"],
        },
    }

    JURISDICTION_HINT_PATTERNS = {
        "tw": [r"taiwan", r"\btw\b", r"台灣", r"中華民國", r"國稅局"],
        "jp": [r"japan", r"\bjp\b", r"日本", r"国税庁"],
        "kr": [r"korea", r"\bkr\b", r"한국", r"국세청"],
        "cn": [r"china", r"\bcn\b", r"中國", r"国家税务总局"],
        "hk": [r"hong kong", r"\bhk\b", r"香港", r"稅務局"],
        "sg": [r"singapore", r"\bsg\b", r"新加坡", r"\biras\b"],
        "us": [r"united states", r"\bu\.s\.\b", r"\busa\b", r"american", r"sec\.gov"],
        "eu": [r"european union", r"\beu\b", r"european commission", r"dac6", r"atad"],
        "in": [r"india", r"\bin\b", r"印度", r"\bcbdt\b", r"\bgst\b"],
    }

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

        intent: Dict = {}
        if use_ai_query_expansion and source_name == "deep_research":
            try:
                intent = self._extract_intent_with_llm(
                    keywords=keywords,
                    user_prompt=user_prompt,
                    provider=provider,
                    model_name=model_name,
                )
            except Exception:
                intent = {}

        if source_name == "deep_research":
            results = self._search_deep_research(
                query=query,
                keywords=keywords,
                user_prompt=user_prompt,
                window=window,
                max_results=max_results,
                ai_variants=ai_variants,
                provider=provider,
                model_name=model_name,
                use_intent_extraction=False,
                precomputed_intent=intent,
            )
        elif source_name in {"all", "google_news_rss_global"}:
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
        ranked = self._rank_results(results, keywords=keywords, user_prompt=user_prompt, intent=intent)
        deduped = self._dedup_by_title_similarity(ranked)
        filtered = [item for item in deduped if item.get("relevance_score", 0.0) >= 1.0]
        return filtered[:max_results]

    SOURCE_HEALTH_FAIL_THRESHOLD = 3
    PARALLEL_FETCH_WORKERS = 6
    DOMAIN_MIN_INTERVAL_SECONDS = 0.7
    DOMAIN_MIN_INTERVAL_OVERRIDES = {
        "efts.sec.gov": 1.1,
        "sec.gov": 1.1,
        "law.moj.gov.tw": 1.0,
        "eur-lex.europa.eu": 0.9,
        "disclosure2.edinet-fsa.go.jp": 1.2,
        "dart.fss.or.kr": 1.2,
    }
    HEAD_PRECHECK_MAX_BYTES = 25 * 1024 * 1024

    def __init__(self):
        self.llm_service = LLMService()
        self._ua_cycle = itertools.cycle(self.POLITE_UA_POOL)
        self._cache_lock = threading.Lock()
        self._fetch_cache: Dict[Tuple[str, str], Tuple[float, requests.Response]] = {}
        self._session = self._build_http_session()
        self._source_stats_lock = threading.Lock()
        self._source_stats: Dict[str, Dict[str, int]] = {}
        self._domain_lock = threading.Lock()
        self._domain_locks: Dict[str, threading.Lock] = {}
        self._domain_last_request: Dict[str, float] = {}

    def _build_http_session(self) -> requests.Session:
        session = requests.Session()
        if Retry is not None:
            retry = Retry(
                total=2,
                connect=2,
                read=1,
                backoff_factor=0.6,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET", "POST"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=32)
        else:
            adapter = HTTPAdapter(pool_connections=16, pool_maxsize=32)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _next_user_agent(self) -> str:
        with self._cache_lock:
            return next(self._ua_cycle)

    def _cached_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        use_cache: bool = True,
    ) -> requests.Response:
        method = method.upper()
        cache_key = (method, self._stable_request_key(url, params, data))
        now = time.time()

        if use_cache:
            with self._cache_lock:
                cached = self._fetch_cache.get(cache_key)
                if cached and now - cached[0] < self.CACHE_TTL_SECONDS:
                    return cached[1]

        merged_headers = {
            "User-Agent": self._next_user_agent(),
            "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7,ja;q=0.6",
            "Accept-Encoding": "gzip, deflate",
        }
        if headers:
            merged_headers.update(headers)

        request_timeout = timeout if timeout is not None else self.SEARCH_TIMEOUT_SECONDS
        self._respect_domain_rate_limit(url)
        try:
            if method == "GET":
                response = self._session.get(url, params=params, headers=merged_headers, timeout=request_timeout)
            else:
                response = self._session.post(url, params=params, data=data, headers=merged_headers, timeout=request_timeout)
        finally:
            self._mark_domain_request(url)

        response.raise_for_status()

        if use_cache and response.status_code == 200:
            with self._cache_lock:
                if len(self._fetch_cache) >= self.CACHE_MAX_ENTRIES:
                    oldest_key = min(self._fetch_cache.items(), key=lambda item: item[1][0])[0]
                    self._fetch_cache.pop(oldest_key, None)
                self._fetch_cache[cache_key] = (now, response)
        return response

    def _stable_request_key(
        self,
        url: str,
        params: Optional[Dict[str, str]],
        data: Optional[Dict[str, str]],
    ) -> str:
        parts = [url]
        if params:
            parts.append("|p=" + "&".join(f"{key}={params[key]}" for key in sorted(params)))
        if data:
            parts.append("|d=" + "&".join(f"{key}={data[key]}" for key in sorted(data)))
        return "".join(parts)

    def _domain_lock_for(self, domain: str) -> threading.Lock:
        with self._domain_lock:
            lock = self._domain_locks.get(domain)
            if lock is None:
                lock = threading.Lock()
                self._domain_locks[domain] = lock
            return lock

    def _min_interval_for_domain(self, domain: str) -> float:
        for suffix, interval in self.DOMAIN_MIN_INTERVAL_OVERRIDES.items():
            if domain == suffix or domain.endswith("." + suffix) or domain.endswith(suffix):
                return interval
        return self.DOMAIN_MIN_INTERVAL_SECONDS

    def _respect_domain_rate_limit(self, url: str):
        domain = self._extract_domain(url)
        if not domain:
            return
        min_interval = self._min_interval_for_domain(domain)
        if min_interval <= 0:
            return
        lock = self._domain_lock_for(domain)
        lock.acquire()
        try:
            last = self._domain_last_request.get(domain, 0.0)
            wait = (last + min_interval) - time.time()
            if wait > 0:
                time.sleep(min(wait, 5.0))
        finally:
            lock.release()

    def _mark_domain_request(self, url: str):
        domain = self._extract_domain(url)
        if not domain:
            return
        self._domain_last_request[domain] = time.time()

    def _head_precheck(self, url: str, max_bytes: Optional[int] = None) -> bool:
        if not url:
            return False
        max_bytes = max_bytes if max_bytes is not None else self.HEAD_PRECHECK_MAX_BYTES
        self._respect_domain_rate_limit(url)
        try:
            response = self._session.head(
                url,
                allow_redirects=True,
                timeout=self.SEARCH_TIMEOUT_SECONDS,
                headers={"User-Agent": self._next_user_agent()},
            )
        except requests.RequestException:
            self._mark_domain_request(url)
            return True
        finally:
            self._mark_domain_request(url)

        if response.status_code in (404, 410, 451):
            return False
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > max_bytes:
            return False
        content_type = (response.headers.get("Content-Type") or "").lower()
        if any(blocked in content_type for blocked in ("video/", "audio/", "image/")):
            return False
        return True

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

    def _search_deep_research(
        self,
        query: str,
        keywords: List[str],
        user_prompt: str,
        window: Dict[str, datetime],
        max_results: int,
        ai_variants: List[str],
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
        use_intent_extraction: bool = True,
        precomputed_intent: Optional[Dict] = None,
    ) -> List[Dict]:
        merged: List[Dict] = []
        seen_urls: set = set()
        candidate_limit = self._candidate_limit(max_results)
        aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        query_variants = self._merge_query_variants(
            keywords=keywords,
            user_prompt=user_prompt,
            ai_variants=ai_variants,
        )

        intent: Dict = precomputed_intent or {}
        if use_intent_extraction and not intent:
            try:
                intent = self._extract_intent_with_llm(
                    keywords=keywords,
                    user_prompt=user_prompt,
                    provider=provider,
                    model_name=model_name,
                )
            except Exception:
                intent = {}
        intent_queries: List[str] = self._build_intent_queries(intent=intent, aliases=aliases)

        for item in self._build_seed_results(keywords=keywords, user_prompt=user_prompt):
            self._append_unique_result(merged, seen_urls, item)

        jurisdictions = self._detect_jurisdictions(keywords=keywords, user_prompt=user_prompt)

        official_tasks: List[Tuple[Callable, Tuple[Any, ...]]] = [
            (self._search_company_sitemap, (aliases, max_results)),
        ]
        primary_query = aliases[0] if aliases else query
        official_tasks.append((self._search_sec_edgar, (primary_query, max_results)))
        for variant in query_variants[:2]:
            official_tasks.append((self._search_sec_edgar, (variant, max_results)))
        for variant in query_variants[:2]:
            official_tasks.append((self._search_eur_lex, (variant, max_results)))
        for variant in query_variants[:2]:
            official_tasks.append((self._search_taiwan_law, (variant, max_results)))
        if "jp" in jurisdictions or any(domain.endswith(".jp") for domain in self._company_domains_for_aliases(aliases)):
            official_tasks.append((self._search_edinet_jp, (primary_query, max_results)))
            for variant in query_variants[:2]:
                official_tasks.append((self._search_edinet_jp, (variant, max_results)))
        if "kr" in jurisdictions or any(domain.endswith(".kr") for domain in self._company_domains_for_aliases(aliases)):
            official_tasks.append((self._search_dart_kr, (primary_query, max_results)))
            for variant in query_variants[:2]:
                official_tasks.append((self._search_dart_kr, (variant, max_results)))

        if self._run_parallel_searches(official_tasks, candidate_limit, merged, seen_urls):
            return merged

        intent_tasks: List[Tuple[Callable, Tuple[Any, ...]]] = []
        for variant in intent_queries[:6]:
            intent_tasks.append((self._search_duckduckgo_html, (variant, max_results)))
            intent_tasks.append((self._search_bing_web, (variant, max_results)))
        if self._run_parallel_searches(intent_tasks, candidate_limit, merged, seen_urls):
            return merged

        targeted_queries = self._build_official_site_queries(
            keywords=keywords,
            user_prompt=user_prompt,
            query_variants=query_variants,
        )
        targeted_tasks: List[Tuple[Callable, Tuple[Any, ...]]] = []
        for targeted_query in targeted_queries[:8]:
            targeted_tasks.append((self._search_duckduckgo_html, (targeted_query, max_results)))
            targeted_tasks.append((self._search_bing_web, (targeted_query, max_results)))
        if self._run_parallel_searches(targeted_tasks, candidate_limit, merged, seen_urls):
            return merged

        news_tasks: List[Tuple[Callable, Tuple[Any, ...]]] = [
            (self._search_google_news_rss, (variant, window, max_results)) for variant in query_variants[:4]
        ]
        if self._run_parallel_searches(news_tasks, candidate_limit, merged, seen_urls):
            return merged

        prf_queries = self._pseudo_relevance_feedback(
            seed_results=merged,
            keywords=keywords,
            user_prompt=user_prompt,
        )
        prf_tasks: List[Tuple[Callable, Tuple[Any, ...]]] = []
        for prf_query in prf_queries[:8]:
            prf_tasks.append((self._search_duckduckgo_html, (prf_query, max_results)))
            prf_tasks.append((self._search_bing_web, (prf_query, max_results)))
        self._run_parallel_searches(prf_tasks, candidate_limit, merged, seen_urls)

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
            aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
            for item in self._safe_search_call(self._search_company_sitemap, aliases, max(4, max_results // 4)):
                self._append_unique_result(merged_items, seen_urls, item)
            primary_alias = aliases[0] if aliases else query
            for item in self._safe_search_call(self._search_sec_edgar, primary_alias, max(4, max_results // 4)):
                self._append_unique_result(merged_items, seen_urls, item)

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

    def _detect_jurisdictions(self, keywords: List[str], user_prompt: str = None) -> List[str]:
        text = " ".join((keywords or []) + [user_prompt or ""]).lower()
        detected: List[str] = []
        for code, patterns in self.JURISDICTION_HINT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    if code not in detected:
                        detected.append(code)
                    break
        return detected

    def _expand_with_thesaurus(
        self,
        keywords: List[str],
        user_prompt: str = None,
        max_concepts: int = 4,
        max_terms_per_concept: int = 6,
    ) -> List[str]:
        text_lower = " ".join((keywords or []) + [user_prompt or ""]).lower()
        triggered_concepts: List[str] = []
        for concept, synonyms in self.TAX_AUDIT_THESAURUS.items():
            if any(synonym.lower() in text_lower for synonym in synonyms):
                triggered_concepts.append(concept)
        if not triggered_concepts:
            triggered_concepts = ["audit", "sampling", "penalty"]

        triggered_concepts = triggered_concepts[:max_concepts]
        aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        jurisdictions = self._detect_jurisdictions(keywords=keywords, user_prompt=user_prompt)

        expansions: List[str] = []
        seen: set = set()

        for concept in triggered_concepts:
            synonyms = self.TAX_AUDIT_THESAURUS.get(concept, [])[:max_terms_per_concept]
            for synonym in synonyms:
                for alias in aliases[:6] or [""]:
                    query = f"{alias} {synonym}".strip() if alias else synonym
                    cleaned = " ".join(query.split())
                    lowered = cleaned.lower()
                    if not cleaned or lowered in seen:
                        continue
                    seen.add(lowered)
                    expansions.append(cleaned)
                    if len(expansions) >= 60:
                        return expansions

        for code in jurisdictions:
            profile = self.JURISDICTION_PROFILE.get(code, {})
            for audit_term in profile.get("audit_terms", [])[:4]:
                for alias in aliases[:4] or [""]:
                    query = f"{alias} {audit_term}".strip()
                    cleaned = " ".join(query.split())
                    lowered = cleaned.lower()
                    if not cleaned or lowered in seen:
                        continue
                    seen.add(lowered)
                    expansions.append(cleaned)
            for filing_term in profile.get("filing_terms", [])[:3]:
                for alias in aliases[:3] or [""]:
                    query = f"{alias} {filing_term}".strip()
                    cleaned = " ".join(query.split())
                    lowered = cleaned.lower()
                    if not cleaned or lowered in seen:
                        continue
                    seen.add(lowered)
                    expansions.append(cleaned)
            for authority in profile.get("authority_aliases", [])[:3]:
                for alias in aliases[:3] or [""]:
                    query = f"{alias} {authority}".strip()
                    cleaned = " ".join(query.split())
                    lowered = cleaned.lower()
                    if not cleaned or lowered in seen:
                        continue
                    seen.add(lowered)
                    expansions.append(cleaned)
            if len(expansions) >= 80:
                break

        for sampling_term in self.AUDIT_SAMPLING_TERMS[:24]:
            for alias in aliases[:3] or [""]:
                query = f"{alias} {sampling_term}".strip()
                cleaned = " ".join(query.split())
                lowered = cleaned.lower()
                if not cleaned or lowered in seen:
                    continue
                seen.add(lowered)
                expansions.append(cleaned)
                if len(expansions) >= 100:
                    return expansions

        return expansions

    def _extract_intent_with_llm(
        self,
        keywords: List[str],
        user_prompt: str = None,
        provider: str = "ollama",
        model_name: str = "qwen3:8b",
    ) -> Dict:
        prompt = f"""
You are a tax-research search planner. Read the user's keywords and intent, then return JSON only:
{{
  "entities": ["primary company / group / subsidiary names, English + local names if known"],
  "jurisdictions": ["ISO 3166-1 alpha-2 country codes most relevant, e.g. TW, JP, KR, CN, HK, SG, US, EU, IN"],
  "time_period": "free-form, e.g. FY2024, last 12 months, 2024 Q3, 113年度",
  "risk_categories": ["audit", "sampling", "penalty", "transfer_pricing", "pillar_two", "cfc", "permanent_establishment", "withholding_tax", "tariff", "vat_gst"],
  "document_types": ["annual_report", "financial_statement", "sustainability_report", "tax_policy", "regulatory_filing", "news", "court_ruling"],
  "focused_subsidiaries": ["names of any specific subsidiaries the user wants drilled into"],
  "must_have_terms": ["1-3 short query phrases that almost certainly appear in good results"],
  "exclude_terms": ["1-3 phrases that signal noise the user does NOT want"]
}}

Original keywords: {keywords}
User intent: {user_prompt or ""}

Rules:
- Only include risk_categories that are clearly implied; default to ["audit", "sampling", "penalty"] when ambiguous.
- jurisdictions must be uppercase ISO codes from the allowed list.
- Keep arrays short (<= 6 items each).
- No prose, no markdown, JSON only.
"""
        schema_hint = {
            "entities": [],
            "jurisdictions": [],
            "time_period": "",
            "risk_categories": [],
            "document_types": [],
            "focused_subsidiaries": [],
            "must_have_terms": [],
            "exclude_terms": [],
        }
        data = self.llm_service.generate_json(
            prompt=prompt,
            schema_hint=schema_hint,
            provider=provider,
            model_name=model_name,
        )
        normalized: Dict = {}
        for key, default in schema_hint.items():
            value = data.get(key, default)
            if isinstance(default, list) and not isinstance(value, list):
                value = []
            if isinstance(value, list):
                cleaned_list = []
                for item in value:
                    if not isinstance(item, str):
                        continue
                    item = item.strip()
                    if item:
                        cleaned_list.append(item)
                normalized[key] = cleaned_list[:6]
            else:
                normalized[key] = value if isinstance(value, str) else ""
        return normalized

    def _build_intent_queries(self, intent: Dict, aliases: List[str]) -> List[str]:
        if not intent:
            return []
        queries: List[str] = []
        seen: set = set()
        primary_entities = intent.get("entities") or aliases or []
        primary_entities = primary_entities[:5]

        risk_lookup = {category: self.TAX_AUDIT_THESAURUS.get(category, []) for category in intent.get("risk_categories") or []}
        if not risk_lookup:
            risk_lookup = {
                "audit": self.TAX_AUDIT_THESAURUS["audit"],
                "sampling": self.TAX_AUDIT_THESAURUS["sampling"],
                "penalty": self.TAX_AUDIT_THESAURUS["penalty"],
            }

        for entity in primary_entities:
            for category, synonyms in risk_lookup.items():
                for synonym in synonyms[:5]:
                    query = f"\"{entity}\" {synonym}"
                    if intent.get("time_period"):
                        query += f" {intent['time_period']}"
                    cleaned = " ".join(query.split())
                    lowered = cleaned.lower()
                    if lowered in seen:
                        continue
                    seen.add(lowered)
                    queries.append(cleaned)

        for entity in primary_entities[:3]:
            for jurisdiction in (intent.get("jurisdictions") or []):
                profile = self.JURISDICTION_PROFILE.get(jurisdiction.lower(), {})
                for audit_term in profile.get("audit_terms", [])[:3]:
                    query = f"\"{entity}\" {audit_term}"
                    cleaned = " ".join(query.split())
                    lowered = cleaned.lower()
                    if lowered in seen:
                        continue
                    seen.add(lowered)
                    queries.append(cleaned)

        for must_have in intent.get("must_have_terms", [])[:3]:
            for entity in primary_entities[:3]:
                query = f"\"{entity}\" {must_have}"
                cleaned = " ".join(query.split())
                lowered = cleaned.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                queries.append(cleaned)

        for subsidiary in intent.get("focused_subsidiaries", [])[:5]:
            for synonym_list in risk_lookup.values():
                for synonym in synonym_list[:3]:
                    query = f"\"{subsidiary}\" {synonym}"
                    cleaned = " ".join(query.split())
                    lowered = cleaned.lower()
                    if lowered in seen:
                        continue
                    seen.add(lowered)
                    queries.append(cleaned)

        return queries[:60]

    def _collect_keyword_service_vocab(self, limit: int = 200) -> List[str]:
        try:
            from services.keyword_service import KeywordService
        except Exception:
            return []
        try:
            service = KeywordService()
            if service.vectorizer is None and getattr(service, "feature_names", None) is None:
                service.train_from_database()
        except Exception:
            return []
        feature_names = getattr(service, "feature_names", []) or []
        if not feature_names:
            return []
        candidates: List[str] = []
        for term in feature_names[:limit]:
            cleaned = " ".join(str(term).split()).strip()
            if not cleaned or self._is_low_value_alias(cleaned):
                continue
            candidates.append(cleaned)
        return candidates

    def _pseudo_relevance_feedback(
        self,
        seed_results: List[Dict],
        keywords: List[str],
        user_prompt: str = None,
        top_terms: int = 6,
    ) -> List[str]:
        if not seed_results:
            return []
        existing_terms = set()
        existing_text = " ".join((keywords or []) + [user_prompt or ""]).lower()
        for token in re.findall(r"[一-鿿]{2,}|[a-zA-Z][a-zA-Z0-9-]{2,}", existing_text):
            existing_terms.add(token.lower())

        token_counts: Dict[str, int] = {}
        for item in seed_results[:25]:
            text = f"{item.get('title', '')} {item.get('snippet', '')}"
            for english_token in re.findall(r"[A-Za-z][A-Za-z0-9.-]{3,}", text):
                lowered = english_token.lower()
                if lowered in existing_terms:
                    continue
                if self._is_low_value_alias(english_token):
                    continue
                token_counts[english_token] = token_counts.get(english_token, 0) + 1
            for cjk_run in re.findall(r"[一-鿿]+", text):
                for length in (4, 3, 2):
                    if len(cjk_run) < length:
                        continue
                    for start in range(0, len(cjk_run) - length + 1):
                        ngram = cjk_run[start:start + length]
                        if ngram.lower() in existing_terms:
                            continue
                        if self._is_low_value_alias(ngram):
                            continue
                        token_counts[ngram] = token_counts.get(ngram, 0) + 1

        for vocab_term in self._collect_keyword_service_vocab(limit=200):
            lowered_vocab = vocab_term.lower()
            if lowered_vocab in existing_terms:
                continue
            for item in seed_results[:25]:
                text_lower = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
                if vocab_term.lower() in text_lower:
                    token_counts[vocab_term] = token_counts.get(vocab_term, 0) + 1

        ranked = sorted(token_counts.items(), key=lambda pair: pair[1], reverse=True)
        candidate_terms = [token for token, count in ranked if count >= 2][:top_terms]
        if not candidate_terms:
            return []

        aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        primary_alias = aliases[0] if aliases else " ".join(keywords or []).strip()
        if not primary_alias:
            return []

        feedback_queries: List[str] = []
        seen: set = set()
        for term in candidate_terms:
            for audit_topic in ("tax audit", "稅務查核", "税務調査"):
                query = f"\"{primary_alias}\" {term} {audit_topic}"
                cleaned = " ".join(query.split())
                lowered = cleaned.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                feedback_queries.append(cleaned)
            for sampling_term in self.AUDIT_SAMPLING_TERMS[:6]:
                query = f"\"{primary_alias}\" {term} {sampling_term}"
                cleaned = " ".join(query.split())
                lowered = cleaned.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                feedback_queries.append(cleaned)

        return feedback_queries[:24]

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
        thesaurus_variants = self._expand_with_thesaurus(keywords=keywords, user_prompt=user_prompt)
        combined = []
        seen = set()

        prioritized = []
        if base_variants:
            prioritized.append(base_variants[0])
        prioritized.extend(ai_variants[:6])
        prioritized.extend(thesaurus_variants[:18])
        prioritized.extend(base_variants[1:])
        prioritized.extend(ai_variants[6:])
        prioritized.extend(thesaurus_variants[18:])

        for variant in prioritized:
            lowered = variant.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            combined.append(variant)
        return combined[:48]

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
        response = self._cached_request("GET", url)
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
        response = self._cached_request("POST", url, data={"q": query})
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

    def _search_sec_edgar(
        self,
        query: str,
        max_results: int,
        forms: str = "10-K,20-F,10-Q,8-K,6-K,40-F"
    ) -> List[Dict]:
        if not query.strip():
            return []
        endpoint = "https://efts.sec.gov/LATEST/search-index"
        params = {
            "q": query,
            "forms": forms,
            "hits": str(min(20, max(max_results, 5))),
        }
        response = self._cached_request(
            "GET",
            endpoint,
            params=params,
            headers={"User-Agent": self.SEC_USER_AGENT, "Accept": "application/json"},
            timeout=self.DEEP_FETCH_TIMEOUT_SECONDS,
        )
        try:
            payload = response.json()
        except ValueError:
            return []
        hits = (payload.get("hits") or {}).get("hits") or []
        results = []
        for hit in hits[:max_results]:
            source = hit.get("_source") or {}
            adsh = (source.get("adsh") or "").strip()
            ciks = source.get("ciks") or []
            display_names = source.get("display_names") or []
            form_name = (source.get("form") or "").strip()
            file_date = source.get("file_date")
            doc_id = (hit.get("_id") or "").strip()
            primary_doc = doc_id.split(":", 1)[1] if ":" in doc_id else ""

            cik = (ciks[0] if ciks else "").lstrip("0") or "0"
            adsh_clean = adsh.replace("-", "")
            if cik and adsh_clean and primary_doc:
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh_clean}/{primary_doc}"
            elif cik and adsh_clean:
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh_clean}/"
            else:
                url = f"https://efts.sec.gov/LATEST/search-index?q={quote_plus(query)}&forms={quote_plus(forms)}"

            issuer = display_names[0] if display_names else "SEC Registrant"
            title = f"SEC EDGAR {form_name or 'Filing'} - {issuer}".strip(" -")
            snippet_pieces = [
                f"Form {form_name}" if form_name else "SEC filing",
                f"filed {file_date}" if file_date else "",
                "; issuer: " + ", ".join(display_names[:2]) if display_names else "",
                "; covers income tax expense, deferred tax, subsidiaries, related party transactions, "
                "uncertain tax positions, transfer pricing, and cross-border tax disclosures.",
            ]
            snippet = "".join(piece for piece in snippet_pieces if piece)

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "sec_edgar",
                "published_at": file_date,
                "relevance_score": 0.0,
            })
        return results

    def _search_eur_lex(self, query: str, max_results: int) -> List[Dict]:
        if not query.strip():
            return []
        url = (
            "https://eur-lex.europa.eu/search.html"
            f"?text={quote_plus(query)}&qid=&type=quick&scope=EURLEX"
        )
        try:
            response = self._cached_request(
                "GET",
                url,
                timeout=self.DEEP_FETCH_TIMEOUT_SECONDS,
                headers={"Accept": "text/html"},
            )
        except requests.RequestException:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for entry in soup.select(".SearchResult, .result"):
            link = entry.select_one("a.title, h3 a, h2 a, a")
            if not link:
                continue
            href = link.get("href") or ""
            if not href:
                continue
            absolute_url = urljoin("https://eur-lex.europa.eu", href)
            title = link.get_text(" ", strip=True) or "EUR-Lex result"
            snippet_node = entry.select_one(".forceIndent, .normal, .ft, p")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            results.append({
                "title": title,
                "url": absolute_url,
                "snippet": snippet or "EUR-Lex official EU regulation, directive, or case-law search result for cross-border tax research.",
                "source": "eur_lex",
                "published_at": None,
                "relevance_score": 0.0,
            })
            if len(results) >= max_results:
                break
        return results

    def _search_taiwan_law(self, query: str, max_results: int) -> List[Dict]:
        if not query.strip():
            return []
        url = (
            "https://law.moj.gov.tw/Search/SearchLaw.aspx"
            f"?ty=ON&kw={quote_plus(query)}"
        )
        try:
            response = self._cached_request(
                "GET",
                url,
                timeout=self.DEEP_FETCH_TIMEOUT_SECONDS,
                headers={"Accept": "text/html"},
            )
        except requests.RequestException:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for row in soup.select("table.tab-list tbody tr, table tr"):
            link = row.select_one("a[href*='LawAll'], a[href*='LawSearchLaw'], a[href*='Law']")
            if not link:
                continue
            href = link.get("href") or ""
            if not href or href.startswith("#"):
                continue
            absolute_url = urljoin("https://law.moj.gov.tw/", href)
            title = link.get_text(" ", strip=True)
            if not title or len(title) < 2:
                continue
            description_node = row.select_one("td:nth-of-type(3), .law-result")
            snippet = description_node.get_text(" ", strip=True) if description_node else ""
            results.append({
                "title": f"全國法規資料庫 - {title}",
                "url": absolute_url,
                "snippet": snippet or "Taiwan official legal database entry covering tax law, customs, and regulatory provisions.",
                "source": "taiwan_law_moj",
                "published_at": None,
                "relevance_score": 0.0,
            })
            if len(results) >= max_results:
                break
        return results

    def _search_edinet_jp(self, query: str, max_results: int) -> List[Dict]:
        if not query.strip():
            return []
        endpoint = "https://disclosure2.edinet-fsa.go.jp/WEEK0010.aspx"
        params = {"uji.verb": "W1E62012CXP01001Action", "uji.bean": "ee.bean.parent.EECommonSearchBean", "TID": "W1E62011", "PID": "W1E62011", "SESSIONKEY": "", "lgKbn": "2", "pkbn": "0", "skbn": "0", "dskb": "", "askb": "", "dflg": "0", "iflg": "0", "preTID1": "", "preTID2": "", "preTID3": "", "preTID4": "", "preTID5": "", "preTID6": "", "preTID7": "", "preTID8": "", "preTID9": "", "preTID10": "", "preTID11": "", "preTID12": "", "preTID13": "", "preTID14": "", "preTID15": "", "nextTID": "", "currentPage": "1", "PreTermPath": "", "fokKbn": "1", "tDocTextSnm": query, "tDocSearchType": "0", "kanrenDocFlg": "0"}
        try:
            response = self._cached_request(
                "GET",
                endpoint,
                params=params,
                timeout=self.DEEP_FETCH_TIMEOUT_SECONDS,
                headers={"Accept": "text/html"},
            )
        except requests.RequestException:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        results: List[Dict] = []
        for row in soup.select("table tr"):
            link = row.find("a", href=True)
            if not link:
                continue
            href = link.get("href") or ""
            if not href:
                continue
            absolute_url = urljoin("https://disclosure2.edinet-fsa.go.jp/", href)
            title = link.get_text(" ", strip=True)
            if not title or len(title) < 4:
                continue
            results.append({
                "title": f"EDINET 開示書類 - {title}",
                "url": absolute_url,
                "snippet": "Japan FSA EDINET disclosure (annual securities report, semiannual report, extraordinary report). Often includes consolidated income tax expense, related party transactions, segment tax breakdown.",
                "source": "edinet_jp",
                "published_at": None,
                "relevance_score": 0.0,
            })
            if len(results) >= max_results:
                break
        return results

    def _search_dart_kr(self, query: str, max_results: int) -> List[Dict]:
        if not query.strip():
            return []
        endpoint = "https://dart.fss.or.kr/dsab007/main.do"
        params = {
            "selectKey": "report",
            "textCrpNm": query,
            "currentPage": "1",
            "maxResults": str(min(20, max(max_results, 5))),
            "maxLinks": "10",
        }
        try:
            response = self._cached_request(
                "GET",
                endpoint,
                params=params,
                timeout=self.DEEP_FETCH_TIMEOUT_SECONDS,
                headers={"Accept": "text/html"},
            )
        except requests.RequestException:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        results: List[Dict] = []
        for row in soup.select("table.tbList tbody tr, table tbody tr"):
            link = row.find("a", href=True)
            if not link:
                continue
            href = link.get("href") or ""
            if not href or href.startswith("#"):
                continue
            absolute_url = urljoin("https://dart.fss.or.kr/", href)
            title = link.get_text(" ", strip=True)
            if not title or len(title) < 4:
                continue
            company_node = row.select_one("td:nth-of-type(2)")
            company = company_node.get_text(" ", strip=True) if company_node else ""
            results.append({
                "title": f"DART 공시 - {company} {title}".strip(),
                "url": absolute_url,
                "snippet": "Korea FSS DART disclosure (사업보고서, 분기보고서, 주요사항보고서). 법인세 비용, 이전가격, 특수관계자 거래, 종속회사 등 한국 상장사의 공시 자료.",
                "source": "dart_kr",
                "published_at": None,
                "relevance_score": 0.0,
            })
            if len(results) >= max_results:
                break
        return results

    def _search_company_sitemap(self, aliases: List[str], max_results: int) -> List[Dict]:
        domains = self._company_domains_for_aliases(aliases)
        if not domains:
            return []
        results = []
        seen_urls = set()
        keyword_pattern = re.compile(
            r"(annual|sustain|esg|tax|investor|ir/|financial|report|governance|risk|"
            r"年報|永續|稅|財報|投資人|關係|報告|公司治理|風險)",
            re.IGNORECASE,
        )

        for domain in domains[:5]:
            for sitemap_url in (
                f"https://{domain}/sitemap.xml",
                f"https://{domain}/sitemap_index.xml",
                f"https://www.{domain}/sitemap.xml",
            ):
                try:
                    response = self._cached_request(
                        "GET",
                        sitemap_url,
                        timeout=self.DEEP_FETCH_TIMEOUT_SECONDS,
                        headers={"Accept": "application/xml,text/xml"},
                    )
                except requests.RequestException:
                    continue

                try:
                    root = ET.fromstring(response.text)
                except ET.ParseError:
                    continue

                for url_node in root.iter():
                    tag = url_node.tag.lower()
                    if not tag.endswith("loc"):
                        continue
                    loc_value = (url_node.text or "").strip()
                    if not loc_value or loc_value in seen_urls:
                        continue
                    if loc_value.lower().endswith(".xml"):
                        try:
                            inner_response = self._cached_request(
                                "GET",
                                loc_value,
                                timeout=self.DEEP_FETCH_TIMEOUT_SECONDS,
                            )
                            inner_root = ET.fromstring(inner_response.text)
                        except (requests.RequestException, ET.ParseError):
                            continue
                        for inner_loc in inner_root.iter():
                            if not inner_loc.tag.lower().endswith("loc"):
                                continue
                            inner_value = (inner_loc.text or "").strip()
                            if not inner_value or inner_value in seen_urls:
                                continue
                            if not keyword_pattern.search(inner_value):
                                continue
                            seen_urls.add(inner_value)
                            results.append({
                                "title": f"{domain} sitemap entry: {inner_value.rsplit('/', 1)[-1] or inner_value}",
                                "url": inner_value,
                                "snippet": (
                                    f"Discovered from {domain} sitemap. Likely relevant to investor relations, "
                                    "annual report, sustainability report, tax governance, financial statement, "
                                    "or subsidiary disclosure."
                                ),
                                "source": "company_sitemap",
                                "published_at": None,
                                "relevance_score": 0.0,
                            })
                            if len(results) >= max_results:
                                return results
                        continue
                    if not keyword_pattern.search(loc_value):
                        continue
                    seen_urls.add(loc_value)
                    results.append({
                        "title": f"{domain} sitemap entry: {loc_value.rsplit('/', 1)[-1] or loc_value}",
                        "url": loc_value,
                        "snippet": (
                            f"Discovered from {domain} sitemap. Likely relevant to investor relations, "
                            "annual report, sustainability report, tax governance, financial statement, "
                            "or subsidiary disclosure."
                        ),
                        "source": "company_sitemap",
                        "published_at": None,
                        "relevance_score": 0.0,
                    })
                    if len(results) >= max_results:
                        return results
                if results:
                    break
        return results

    def _safe_search_call(self, search_func, *args) -> List[Dict]:
        source_name = getattr(search_func, "__name__", "unknown")
        if self._is_source_unhealthy(source_name):
            return []
        try:
            results = search_func(*args)
            self._record_source_outcome(source_name, success=True)
            return results
        except Exception:
            self._record_source_outcome(source_name, success=False)
            return []

    def _record_source_outcome(self, source_name: str, success: bool):
        with self._source_stats_lock:
            stats = self._source_stats.setdefault(source_name, {"success": 0, "fail": 0, "consecutive_fail": 0})
            if success:
                stats["success"] += 1
                stats["consecutive_fail"] = 0
            else:
                stats["fail"] += 1
                stats["consecutive_fail"] += 1

    def _is_source_unhealthy(self, source_name: str) -> bool:
        with self._source_stats_lock:
            stats = self._source_stats.get(source_name)
            if not stats:
                return False
            return stats["consecutive_fail"] >= self.SOURCE_HEALTH_FAIL_THRESHOLD

    def get_source_health_snapshot(self) -> Dict[str, Dict[str, int]]:
        with self._source_stats_lock:
            return {name: dict(values) for name, values in self._source_stats.items()}

    def _run_parallel_searches(
        self,
        tasks: List[Tuple[Callable, Tuple[Any, ...]]],
        candidate_limit: int,
        merged: List[Dict],
        seen_urls: set,
    ) -> bool:
        if not tasks:
            return False
        max_workers = min(self.PARALLEL_FETCH_WORKERS, max(2, len(tasks)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._safe_search_call, fn, *args) for fn, args in tasks]
            for future in as_completed(futures):
                try:
                    items = future.result() or []
                except Exception:
                    items = []
                for item in items:
                    self._append_unique_result(merged, seen_urls, item)
                if len(merged) >= candidate_limit:
                    for pending in futures:
                        pending.cancel()
                    return True
        return False

    def _dedup_by_title_similarity(self, results: List[Dict], threshold: float = 0.7) -> List[Dict]:
        if not results:
            return results
        deduped: List[Dict] = []
        seen_signatures: List[set] = []
        for item in results:
            title = (item.get("title") or "").strip()
            if not title:
                deduped.append(item)
                continue
            tokens = self._title_signature(title)
            if not tokens:
                deduped.append(item)
                continue
            duplicate_index = -1
            for index, signature in enumerate(seen_signatures):
                jaccard = self._jaccard(tokens, signature)
                if jaccard >= threshold:
                    duplicate_index = index
                    break
            if duplicate_index >= 0:
                existing = deduped[duplicate_index]
                if (item.get("relevance_score") or 0.0) > (existing.get("relevance_score") or 0.0):
                    existing.setdefault("duplicate_titles", []).append(existing.get("title"))
                    existing.update({k: v for k, v in item.items() if k != "duplicate_titles"})
                else:
                    existing.setdefault("duplicate_titles", []).append(title)
                continue
            seen_signatures.append(tokens)
            deduped.append(item)
        return deduped

    def _title_signature(self, title: str) -> set:
        cleaned = re.sub(r"[\s\-—\|·•:：、，,。.（）()『』「」\"'’“”/\\]", " ", title.lower())
        tokens = set()
        for english_token in re.findall(r"[a-z][a-z0-9]{2,}", cleaned):
            tokens.add(english_token)
        for cjk_run in re.findall(r"[一-鿿]+", cleaned):
            for length in (3, 2):
                if len(cjk_run) < length:
                    continue
                for start in range(0, len(cjk_run) - length + 1):
                    tokens.add(cjk_run[start:start + length])
        return tokens

    def _jaccard(self, left: set, right: set) -> float:
        if not left or not right:
            return 0.0
        intersection = left & right
        union = left | right
        if not union:
            return 0.0
        return len(intersection) / len(union)

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
        response = self._cached_request("GET", url)
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

    def _rank_results(
        self,
        results: List[Dict],
        keywords: List[str],
        user_prompt: str = None,
        intent: Optional[Dict] = None,
    ) -> List[Dict]:
        prompt_terms = re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9_-]{2,}", (user_prompt or "").lower())
        entity_aliases = self._extract_entity_aliases(keywords=keywords, user_prompt=user_prompt)
        event_intent = self._has_tax_event_intent(keywords=keywords, user_prompt=user_prompt)
        intent = intent or {}
        exclude_terms = [term.lower() for term in (intent.get("exclude_terms") or []) if isinstance(term, str)]
        must_have_terms = [term.lower() for term in (intent.get("must_have_terms") or []) if isinstance(term, str)]

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
            sampling_hits = sum(
                1.4
                for phrase in self.AUDIT_SAMPLING_TERMS
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
            source_bonus += 1.8 if result.get("source") == "sec_edgar" else 0.0
            source_bonus += 1.5 if result.get("source") == "eur_lex" else 0.0
            source_bonus += 1.5 if result.get("source") == "taiwan_law_moj" else 0.0
            source_bonus += 1.6 if result.get("source") == "edinet_jp" else 0.0
            source_bonus += 1.6 if result.get("source") == "dart_kr" else 0.0
            source_bonus += 1.2 if result.get("source") == "company_sitemap" else 0.0
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
            exclude_penalty = sum(2.5 for term in exclude_terms if term and term in haystack)
            must_have_bonus = sum(1.6 for term in must_have_terms if term and term in haystack)

            result["domain"] = domain
            result["result_type"] = self._infer_result_type(result)
            result["match_reasons"] = self._build_match_reasons(
                result=result,
                keywords=keywords,
                prompt_terms=prompt_terms,
                entity_aliases=entity_aliases,
                official_bonus=official_bonus,
                disclosure_bonus=disclosure_bonus,
                pdf_bonus=pdf_bonus,
                intent=intent,
            )
            result["relevance_score"] = round(
                keyword_hits
                + prompt_hits
                + tax_phrase_hits
                + tax_event_hits
                + sampling_hits
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
                + must_have_bonus
                - weak_topic_penalty
                - social_penalty
                - generic_reference_penalty
                - unrelated_company_penalty
                - event_document_penalty
                - exclude_penalty,
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
        pdf_bonus: float,
        intent: Optional[Dict] = None,
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

        matched_sampling_terms = [
            term
            for term in self.AUDIT_SAMPLING_TERMS
            if term.lower() in haystack or term.lower() in (result.get("url", "").lower())
        ][:3]
        if matched_sampling_terms:
            reasons.append(f"命中抽樣／選案查核線索：{', '.join(matched_sampling_terms)}")

        if pdf_bonus > 0:
            reasons.append("PDF / 文件型資料優先")

        if result.get("published_at"):
            reasons.append("有可用發布時間")

        if result.get("is_historical_context"):
            reasons.append("歷史稅務事件脈絡")

        intent = intent or {}
        must_have_terms = [term for term in (intent.get("must_have_terms") or []) if isinstance(term, str)]
        matched_must_have = [term for term in must_have_terms if term.lower() in haystack][:2]
        if matched_must_have:
            reasons.append(f"命中意圖必含詞：{', '.join(matched_must_have)}")

        exclude_terms = [term for term in (intent.get("exclude_terms") or []) if isinstance(term, str)]
        matched_exclude = [term for term in exclude_terms if term.lower() in haystack][:2]
        if matched_exclude:
            reasons.append(f"命中意圖排除詞 (扣分)：{', '.join(matched_exclude)}")

        if not reasons:
            reasons.append("語意相近且整體相關")

        return reasons[:5]

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

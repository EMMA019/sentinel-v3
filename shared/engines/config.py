import os

def _ei(key, default):
    v = os.getenv(key, "").strip()
    return int(v) if v else default

def _ef(key, default):
    v = os.getenv(key, "").strip()
    return float(v) if v else default

CONFIG = {
    "CAPITAL_JPY":       _ei("CAPITAL_JPY",       1_000_000),
    "MAX_POSITIONS":     _ei("MAX_POSITIONS",      20),
    "ACCOUNT_RISK_PCT":  _ef("ACCOUNT_RISK_PCT",   0.015),
    "MAX_SAME_SECTOR":   _ei("MAX_SAME_SECTOR",    2),
    "MIN_RS_RATING":     _ei("MIN_RS_RATING",      70),
    "MIN_VCP_SCORE":     _ei("MIN_VCP_SCORE",      55),
    "MIN_PROFIT_FACTOR": _ef("MIN_PROFIT_FACTOR",  1.1),
    "STOP_LOSS_ATR":     _ef("STOP_LOSS_ATR",      2.0),
    "TARGET_R_MULTIPLE": _ef("TARGET_R_MULTIPLE",  2.5),
    "CACHE_EXPIRY":      12 * 3600,
}

# NASDAQ 100
_NASDAQ100 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","COST",
    "NFLX","TMUS","AMD","PEP","LIN","CSCO","ADBE","INTU","TXN","QCOM",
    "AMAT","ISRG","BKNG","HON","VRTX","PANW","ADP","MU","SBUX","GILD",
    "LRCX","MRVL","REGN","KLAC","MDLZ","SNPS","CDNS","ADI","MELI","CRWD",
    "CEG","CTAS","ORLY","CSX","ASML","FTNT","MAR","PCAR","KDP","DASH",
    "MNST","WDAY","FAST","ROST","PAYX","DXCM","AEP","EA","CTSH","GEHC",
    "IDXX","ODFL","LULU","XEL","BKR","ON","KHC","EXC","VRSK","FANG",
    "BIIB","TTWO","GFS","ARM","TTD","ANSS","DLTR","WBD","NXPI","ROP",
    "CPRT","CSGP","CHTR","ILMN","MDB","ZS","TEAM","DDOG","NET","ZM",
    "OKTA","DOCU","RIVN","LCID","SMCI","MSTR","PLTR","APP","SIRI","PARA",
]

# ダウ 30
_DOW30 = [
    "AAPL","AMGN","AXP","BA","CAT","CRM","CSCO","CVX","DIS","DOW",
    "GS","HD","HON","IBM","INTC","JNJ","JPM","KO","MCD","MMM",
    "MRK","MSFT","NKE","PG","SHW","TRV","UNH","V","VZ","WMT",
]

# ラッセル2000 注目銘柄（流動性・成長性重視）
_RUSSELL2000 = [
    # ヘルスケア・バイオ
    "ACAD","ACHC","AGIO","ALKS","ALNY","AMPH","ARDX","ARWR","AXSM",
    "BMRN","BPMC","CERE","CHRS","CMPS","CNMD","COHU","DVAX","EOLS",
    "FIXX","FOLD","GKOS","HALO","HIMS","IMCR","INVA","IONS","IOVA",
    "ITCI","JANX","JAZZ","KROS","KURA","KYMR","LNTH","MGNX","MNKD",
    "MRUS","MYGN","NKTR","NVCR","OCGN","ORIC","PRCT","PRGO","PRTA",
    "PTCT","PTGX","RCUS","RLAY","ROIV","RPRX","RYTM","SAGE","SANA",
    "SEER","SMMT","VKTX","RARE","UTHR","HOLX","RXRX","TMDX","INSP",
    "IRTC","LIVN","NARI","SWAV","ACMR","NTRA","EXAS","NEOG","INCY",
    # テクノロジー・SaaS
    "ACLS","AGYS","AMBA","APPN","AVAV","BAND","BIGC","BRZE","CDAY",
    "CLFD","DAVE","DCBO","DLB","DOMO","EGAN","EGHT","ENVX","EXPI",
    "EXTR","FARO","FLNC","FROG","GBTG","GDRX","GLBE","GTLB","HCAT",
    "HEAR","SOUN","IONQ","OKLO","PATH","MNDY","IOT","DUOL","CFLT",
    "BBAI","CIEN","VIAV","IPGP","RXRX","IIVI","SAIL","VRNS","QLYS",
    # 消費・小売
    "BKE","BJRI","BLMN","BOOT","BRCC","BYND","CAKE","CALM","CATO",
    "CBRL","CENT","CENTA","CONN","CRSR","CSTE","CSWI","DRVN","EVTC",
    "WING","CAVA","CART","ONON","DECK","LULU","CROX","CELH","ELF",
    "SKIN","XPOF","BIRK","BOOT","BKE","PLNT","MODG","OXM","GFF",
    # 産業・エネルギー・素材
    "AEIS","AEHR","ALEX","ALG","ALGT","AMRC","AMSC","AMPS","AMTX",
    "AMWD","APOG","APPF","APYX","AQMS","ARLO","AROC","ARRY","ARVN",
    "ATKR","ATRC","ATSG","AZTA","BCC","BCPC","BLBD","BRC","BTG","BW",
    "CALM","CANO","CCJ","CDMO","CDNA","CEVA","CLPS","CMCO","CODA",
    "COLB","COOK","CPRX","CRAI","CRAW","CRIS","CTBI","CTRE","DQ",
    "DUOS","EKSO","ELVN","EMBC","EMKR","ENVB","EPRT","FCNCA","FORM",
    "GIGA","GLNG","GLPI","GOOS","GORV","GPCR","GREE","GRND","GURE",
    "HLNE","HMST","HNNA","HNRG","HIPO","MDXG","MGTX","NRIX","NTST",
    "NVET","ONEM","OPCH","PHAT","RPID","RDUS","RNST","UEC","URA",
    "UUUU","DNN","NXE","SCCO","AA","NUE","STLD","CLF","MP","ALTM",
    # フィンテック・暗号資産
    "AFRM","UPST","SOFI","DKNG","HOOD","MARA","RIOT","BITF","HUT",
    "IREN","WULF","CORZ","CIFR","CLSK","APLD","NBIS","ALAB","CLS",
    "FUTU","TIGR","NRDS","PFSI","GHLD","RCKT","LDI","UWMC","ESNT",
]

# コア（S&P500主要・高流動性）
_CORE = [
    # 半導体
    "NVDA","AMD","AVGO","TSM","ASML","MU","QCOM","MRVL","LRCX","AMAT","KLAC",
    "ADI","ON","SMCI","ARM","MPWR","TER","COHR","APH","TXN","GLW","INTC",
    "STM","WOLF","SWKS","QRVO","MCHP","ENTG","ONTO","AMKR","CAMT",
    # ビッグテック・クラウド・サイバー
    "MSFT","GOOGL","META","AAPL","AMZN","NFLX","CRM","NOW","SNOW","ADBE",
    "INTU","ORCL","IBM","CSCO","ANET","NET","PANW","CRWD","PLTR","ACN",
    "ZS","OKTA","FTNT","CYBR","S","TENB","VRNS","QLYS","SAIL",
    # AI・インフラ
    "APLD","VRT","ALAB","NBIS","CLS","IONQ","OKLO","DDOG","MDB","HUBS",
    "TTD","APP","GTLB","IOT","DUOL","CFLT","AI","PATH","MNDY","RXRX",
    "SOUN","BBAI","CIEN","LITE","IPGP","VIAV",
    # 金融・保険・決済
    "BRK-B","JPM","GS","MS","BAC","WFC","C","AXP","V","MA","COIN","MSTR",
    "HOOD","PYPL","SOFI","AFRM","UPST","SCHW","BX","BLK","SPGI","MCO",
    "CB","TRV","PGR","AIG","AFL","MET","PRU","CINF",
    "ICE","CME","NDAQ","CBOE","FIS","FI","GPN","JKHY","WEX",
    # ヘルスケア・バイオ・医療機器
    "UNH","LLY","ABBV","REGN","VRTX","NVO","BSX","ISRG","TMO","ABT",
    "MRNA","BNTX","MDT","CI","ELV","HCA","HOLX","DVAX","SMMT","VKTX",
    "CRSP","NTLA","BEAM","UTHR","RARE","OMER","GILD","AMGN","BIIB",
    "INCY","EXAS","NTRA","NEOG","TMDX","INSP","IRTC","LIVN","NARI","SWAV",
    "HIMS","ACAD","ALNY","IONS","ARWR","PTCT","RXRX","KYMR","JANX","BPMC",
    # 消費・小売・外食・ブランド
    "COST","WMT","HD","MCD","SBUX","NKE","MELI","BABA","TSLA","CVNA",
    "LULU","ONON","DECK","CROX","WING","CMG","DPZ","YUM","CELH","MNST",
    "CART","CAVA","ROST","TJX","LOW","TGT","ORLY","AZO","EBAY","ETSY",
    "W","CHWY","ELF","SKIN","BIRK","TPR","CPRI","BOOT","BKE","PLNT",
    # エネルギー
    "XOM","CVX","COP","EOG","SLB","OXY","VLO","PSX","MPC","FCX","CCJ",
    "URA","UUUU","DNN","NXE","UEC","AM","TRGP","OKE","WMB","KMI","ET",
    "CTRA","DVN","FANG","MRO","APA","HAL","BKR","NOV","WHD",
    # 産業・防衛・航空宇宙
    "GE","GEV","ETN","CAT","HON","DE","LMT","RTX","BA","GD","HII","AXON",
    "LHX","NOC","TDG","ROP","URI","PCAR","CMI","NSC","UNP","CSX","FDX",
    "RKLB","ASTS","BE","LUNR","RCL","DAL","UAL","ALK","AAL",
    "TT","CARR","OTIS","AME","RRX","GWW","FAST","MLI",
    # 不動産・公共・インフラ
    "NEE","DUK","SO","AEP","EXC","XEL","ED","D","PCG","EIX","WEC","AWK",
    "AMT","EQIX","PLD","CCI","DLR","O","PSA","WELL","IRM","VICI","GLPI",
    "SPG","EQR","AVB","MAA","NNN","STAG",
    # テレコム・メディア・エンタメ
    "TMUS","VZ","CMCSA","DIS","SPOT","RDDT","RBLX","UBER","ABNB","BKNG",
    "MAR","HLT","DKNG","SOUN","GME","PARA","WBD","AMCX","PINS",
    "YELP","Z","EXPE","LMND","FUBO",
    # 素材・鉱業・化学
    "NUE","STLD","AA","SCCO","FCX","NEM","AEM","WPM","RGLD","CLF",
    "MP","ALTM","OLN","CE","EMN","LYB","DOW","LIN","APD","SHW",
    # ETF
    "SPY","QQQ","IWM","SMH","XLF","XLV","XLE","XLI","XLK","XLC","XLY",
    "XLRE","XLP","XLB","XLU","GLD","SLV","USO","TLT","HYG","ARKK",
    "SOXX","IBB","XBI","KRE","HACK","BOTZ","CIBR","CLOU","WCLD",
]

TICKERS = sorted(list(set(_NASDAQ100 + _DOW30 + _RUSSELL2000 + _CORE)))

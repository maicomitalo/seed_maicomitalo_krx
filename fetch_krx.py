import os
import csv
import requests
from datetime import datetime, timedelta

CSV_PATH = "data/KRX_FOREIGN_NET.csv"

def get_krx_foreign_net(target_date_str):
    url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020301"
    }
    # Parâmetros oficiais da tabela de tendência por investidor (KOSPI)
    payload = {
        "bld": "dbms/MDC/STAT/standard/MDCSTAT02201",
        "locale": "ko_KR",
        "inqTpCd": "1",
        "trdVolVal": "2",      # 2 = Valor financeiro (KRW)
        "askBid": "3",         # 3 = Compra líquida (순매수)
        "mktId": "STK",        # STK = KOSPI (use KSQ para KOSDAQ)
        "strtDd": target_date_str,
        "endDd": target_date_str
    }

    session = requests.Session()

session.headers.update({
    "User-Agent": headers["User-Agent"],
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://data.krx.co.kr",
    "X-Requested-With": "XMLHttpRequest"
})

# Inicializa a sessão no site oficial
session.get(
    "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd?screenId=MDCSTAT022",
    timeout=15
)

# Realiza a consulta
response = session.post(
    "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
    data=payload,
    headers={
        "Referer": "https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd?screenId=MDCSTAT022"
    },
    timeout=20
)

print("Status HTTP:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("Resposta recebida:", response.text[:500])

response.raise_for_status()

try:
    data = response.json()
except ValueError:
    raise RuntimeError(
        "O KRX não retornou JSON. Verifique a resposta impressa acima."
    )

    # Procura a linha de Estrangeiros (외국인)
    for row in data.get("output", []):
        if "외국인" in row.get("INVST_TP_NM", ""):
            # O KRX retorna em Won; dividimos por 1 bilhão (십억원)
            raw_val = row.get("NETBID_TRDVAL", "0").replace(",", "")
            if raw_val and raw_val != "-":
                return round(float(raw_val) / 1_000_000_000, 2)
    return None

def update_csv(date_str, value):
    rows = {}
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, "r", newline="") as f:
            for row in csv.reader(f):
                if row:
                    rows[row[0]] = row

    date_key = f"{date_str}T"
    rows[date_key] = [date_key, str(value), str(value), str(value), str(value), "0"]

    # Ordena cronologicamente (obrigatório no Pine Seeds)
    sorted_keys = sorted(rows.keys())
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        for k in sorted_keys:
            writer.writerow(rows[k])

if __name__ == "__main__":
    # Às 6h no Brasil (BRT), já são 18h na Coreia (KST) e o pregão já fechou
    today_kst = (datetime.utcnow() + timedelta(hours=9)).strftime("%Y%m%d")
    val = get_krx_foreign_net(today_kst)

    if val is not None:
        update_csv(today_kst, val)
        print(f"Atualizado {today_kst}: {val} bilhões KRW")
    else:
        print(f"Sem dados de pregão para {today_kst} (feriado ou fim de semana).")

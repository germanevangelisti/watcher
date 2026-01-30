import os
import datetime
import requests
import random
import time

def daterange(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + datetime.timedelta(n)

def download_boletines(start_date, end_date, output_dir="boletines"):
    os.makedirs(output_dir, exist_ok=True)
    base_url = "https://boletinoficial.cba.gov.ar/wp-content/4p96humuzp/{year}/{month:02d}/{section}_Secc_{day:02d}{month:02d}{y_short}.pdf"
    
    sections = ["1", "2", "3", "4", "5"]
    
    for single_date in daterange(start_date, end_date):
        # Omit weekends
        if single_date.weekday() >= 5:
            continue
        
        y = single_date.year
        y_short = int(str(single_date.year)[2:])
        m = single_date.month
        d = single_date.day

        for sec in sections:
            time.sleep(random.uniform(1.3, 2.5))
            url = base_url.format(year=y, y_short=y_short, month=m, section=sec, day=d)
            fname = f"{y}{m:02d}{d:02d}_{sec}_Secc.pdf"
            path = os.path.join(output_dir, fname)
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
                    "Accept": "application/pdf",
                }
                resp = requests.get(url, timeout=10, headers=headers)
                if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith("application/pdf"):
                    with open(path, "wb") as f:
                        f.write(resp.content)
                    print(f"[+] Descargado: {fname}")
                else:
                    print(f"[-] No disponible: {fname} (status {resp.status_code})")
            except Exception as e:
                print(f"[!] Error descargando {fname}: {e}")

# Ejemplo de uso:
if __name__ == "__main__":
    start = datetime.date(2025, 8, 1)
    end = datetime.date(2025, 8, 24)
    download_boletines(start, end)
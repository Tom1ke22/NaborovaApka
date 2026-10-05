FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint skopírujeme MIMO /app, aby volume mount v dev móde ho neprekryl
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . .

# Appka nebeží ako root: kto by ju cez chybu ovládol, nemá root v kontejneri.
# Kód patrí rootovi (appka ho nesmie prepisovať), zapisovať smie len do
# uploads/, kam LocalStorage ukladá CV.
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /app/uploads \
    && chown app:app /app/uploads
USER app

ENTRYPOINT ["/entrypoint.sh"]
# --proxy-headers + --forwarded-allow-ips: appka beží za reverznou proxy
# (nginx, Cloud Run), takže request.client.host je IP proxy, nie klienta.
# Bez týchto prepínačov sa rate limit kľúčuje na proxy a platí spoločne pre
# všetkých uchádzačov. "*" je bezpečné len vtedy, keď sa ku kontejneru nedá
# dostať inak než cez proxy (presne prípad Cloud Run); pri vlastnom hostingu
# sem daj konkrétnu adresu proxy.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]

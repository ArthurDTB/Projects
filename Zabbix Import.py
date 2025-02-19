import requests
import urllib3
import pandas as pd
from datetime import timedelta

fuso_brasilia = pytz.timezone('America/Sao_Paulo')

# Dicionário Das Lat e Lon
coordenadas = {
    #Coordenadas inseridas manualmente caso seu Geopy ou integração com geolocalizadores de algum problema.
}

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

usarname = "user"
password = "pass"

url = "URL do seu domínio"
headers = {
    "Content-Type": "application/json"
}

# ----------------------- Inicio da consulta Para Solicitar um Token -----------------------
token_payload = {
    "jsonrpc": "2.0",
    "method": "user.login",
    "params": {
        "username": usarname,
        "password": password
    },
    "id": 1
}

token_response = requests.post(url, json=token_payload, headers=headers)
token = ""

if token_response.status_code == 200:             # Valida a consulta
    token = token_response.json()['result']       # Passa o Retorno da API (token) para a Variavél

# ----------------------- Fim da consulta Para Solicitar um Token -----------------------


# ----------------------- Inicio da consulta de ID e Nomes dos Serviços -----------------------
services_payload = {
    "jsonrpc": "2.0",
    "method": "service.get",
    "params": {
        "output": ["serviceid", "name"],  # Especificando que queremos o ID e o nome
    },
    "auth": token,
    "id": 2
}

service_response = requests.post(url, json=services_payload, headers=headers)
servicos_id_nome = {}

if service_response.status_code == 200:
    data_dict = service_response.json()['result']       # Coleta o resultado da consulta de Serviços

    for valores in data_dict:
        if valores['serviceid'] != '4':  # Se Houver Necessidade de Ignorar Algum Serviço
            servicos_id_nome [valores['serviceid']] = valores['name']      # Atribui todos os Chave e Valor para o dicionário "servicos_id_nome" 

# ----------------------- Fim da consulta de ID e Nomes dos Serviços -----------------------

# ----------------------- Consulta Analise de ID e Nomes dos SLA -----------------------
slaId_payload = {
    "jsonrpc": "2.0",
    "method": "sla.get",
    "params": {
        "output": ["slaid","name",]
    },
    "auth": token,
    "id": 2
}

slaId_response = requests.post(url, json=slaId_payload, headers=headers)
slaids = {}
rows = []
# ----------------------- Fim da Consulta Analise de ID e Nomes dos SLA -----------------------

if slaId_response.status_code == 200:
    data_dict = slaId_response.json()['result']       # Coleta o resultado da consulta de SLA

    for valores in data_dict:
        if valores['slaid'] != '3':     # Se Houver Necessidade de Ignorar Algum SLA
            slaids [valores['slaid']] = valores['name']      # Atribui todos os Chave e Valor para o dicionário "slaids" 
    
    # ----------------------- Consulta Análise de SLA Diário (Retorna as Métricas dos SLA) -----------------------
    for slaid in slaids:
        payload_diario = {
            "jsonrpc": "2.0",
            "method": "sla.getsli",
            "params": {
                "slaid": slaid
            },
            "auth": token,
            "id": 1
        }
        response_diario = requests.post(url, json=payload_diario, headers=headers, verify=False)
    # ----------------------- Fim da Consulta Análise de SLA Diário (Retorna as Métricas dos SLA) -----------------------

        if response_diario.status_code == 200:
            data_dict = response_diario.json()['result']        # Passando os Dados para as Variáveis
            periods = data_dict['periods']
            service_ids = data_dict['serviceids']
            sli = data_dict['sli']

            for idx, sli_item in enumerate(sli):                # Percorre a lista de listas que é retornado no "sli"
                period = periods[idx]
                period_from = period['period_from']
                period_to = period['period_to']
                service_ids_period = service_ids[:len(sli_item)] 

                for i, sli_data in enumerate(sli_item):
                    service_id = service_ids_period[i]
                    sli_value = sli_data['sli']
                    meta = 99/100

                    if sli_value == -1:
                        continue  # Pula esse SLAID, mas continua com os outros, por isso o desuso do break

                    uptime = sli_data['uptime']
                    downtime = sli_data['downtime']
                    error_budget = sli_data['error_budget']

                    name_event = ""
                    if sli_data['excluded_downtimes'] == []:                    # Verifica se não há eventos de downtime excluídos
                        excluded_downtimes = sli_data['excluded_downtimes']
                        name_event = "Sem Evento"
                    else:                                                       # Caso existam downtimes excluídos, 
                        for downtime_event in sli_data['excluded_downtimes']:
                            name_event = downtime_event['name']
                            period_from_event = pd.to_datetime(downtime_event['period_from'], unit='s').strftime("%d-%m-%Y %H:%M:%S")   # Converte os timestamps do formato Unix para data legível
                            period_to_event = pd.to_datetime(downtime_event['period_to'], unit='s').strftime("%d-%m-%Y %H:%M:%S")       # Converte os timestamps do formato Unix para data legível
                            excluded_downtimes = str(f"Inicio: {period_from_event} - Fim: {period_to_event}")

                    if sli_value > meta:
                        critico = "Não Critico"
                    else:
                        critico = "Critico"

                    period_from = pd.to_datetime(period_from, unit='s', utc=True)
                    period_to = pd.to_datetime(period_to, unit='s',utc=True)
                    period_from = period_from.tz_convert(fuso_brasilia)
                    period_to = period_to.tz_convert(fuso_brasilia)
                    period_from = period_from.tz_localize(None)
                    period_to = period_to.tz_localize(None)
                    uptime = str(timedelta(seconds=uptime))
                    if "day" in uptime:
                        days, time = uptime.split(", ")  # Separa "1 day" e "00:00:00"
                        total_days = int(days.split()[0])  # Obtém o número de dias
                        hours, minutes, seconds = map(int, time.split(":"))  # Quebra o tempo restante
                        uptime = f"{total_days}.{hours:02}:{minutes:02}:{seconds:02}"  # Formato d.hh:mm:ss
                    else:
                        uptime = uptime  # Mantém no formato hh:mm:ss se não houver dias

                    # Converter downtime para usar o formato Duration formato do Power BI
                    downtime = str(timedelta(seconds=downtime))
                    if "day" in downtime:
                        days, time = downtime.split(", ")  # Separa "1 day" e "00:00:00"
                        total_days = int(days.split()[0])  # Obtém o número de dias
                        hours, minutes, seconds = map(int, time.split(":"))  # Quebra o tempo restante
                        downtime = f"{total_days}.{hours:02}:{minutes:02}:{seconds:02}"  # Formato d.hh:mm:ss
                    else:
                        downtime = downtime  # Mantém no formato hh:mm:ss se não houver dias
                    error_budget = str(timedelta(seconds=error_budget))
                    if "day" in error_budget:
                        days, time = error_budget.split(", ")  # Separa "1 day" e "00:00:00"
                        total_days = int(days.split()[0])  # Obtém o número de dias
                        hours, minutes, seconds = map(int, time.split(":"))  # Quebra o tempo restante
                        error_budget = f"{total_days}.{hours:02}:{minutes:02}:{seconds:02}"  # Formato d.hh:mm:ss
                    else:
                        error_budget = error_budget  # Mantém no formato hh:mm:ss se não houver dias
                    servico_id_nome = servicos_id_nome.get(str(service_id))
                    servico_lat_lon = coordenadas.get(service_id)

                    if(sli_value < 99):                             # Cria o Sinaleiro que será usado posteriormente no power bi
                        monitoramento = "Vermelho"
                    elif(sli_value >= 99 and sli_value < 99.7):
                        monitoramento = "Amarelo"
                    else:
                        monitoramento = "Verde"
                    
                    row = {

                        'Period From': period_from,
                        'Period To': period_to,
                        #'Hours': Hours,
                        #'Period': period,
                        'Service ID': service_id,
                        'Service Name': servico_id_nome,
                        'Uptime': uptime,
                        'Downtime': downtime,
                        'SLI': round(sli_value/100, 4),
                        'Error Budget': error_budget,
                        'Name Event': name_event,
                        'Excluded Downtimes': excluded_downtimes,
                        'Criticidade': critico,
                        'Meta': meta,
                        'Service Lat': servico_lat_lon[0],
                        'Service Lon': servico_lat_lon[1],
                        'Estado': servico_lat_lon[2],
                        'Monitoramento': monitoramento,
                        'Análise': "Diária"
                    }
                    rows.append(row)



df = pd.DataFrame(rows)
print(df)

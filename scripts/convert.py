#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
from PyPDF2 import PdfFileReader
import tabula

path = '.'
comuni = pd.DataFrame(pd.read_csv('https://raw.githubusercontent.com/gabacode/vaxExtract/main/utilities/Elenco-comuni-siciliani.csv', converters={'pro_com_t': '{:0>6}'.format}))
latest = pd.DataFrame(pd.read_csv(path+'/download/report.csv')).iloc[-1]
file = latest['nome_file']
date = latest['data_report']


def getRanges(file):
    '''
    Estrae i range delle pagine
    Allegato 1 e Allegato 2
    '''

    result_list = []
    r_pages = []

    reader = PdfFileReader(file)
    pages = reader.numPages

    for page_number in range(0, pages):
        page = reader.getPage(page_number)
        page_content = page.extractText()

        if "ALLEGATO" in page_content:
            result = {"page": page_number}
            result_list.append(result)

    r_pages.append(pages)

    for i in range(len(result_list)):
        r_pages.append(result_list[i]['page'])

    r_pages.sort()

    allegati = {
        "file": file,
        "incidenza": [r_pages[0], r_pages[1]],
        "vaccini": [r_pages[1]+1, r_pages[2]]
    }

    return allegati


def isDigit(x):
    '''
    True se x contiene un numero
    '''
    try:
        float(x)
        return True
    except ValueError:
        return False


def getVax(vax):
    # Leggi il PDF  VAX con tabula-py
    print('Leggo tabella Vaccini...attendi...')
    pages = vax['vaccini']
    #pages = list(range(vax['vaccini'][0], vax['vaccini'][1]+1))
    pdf = tabula.read_pdf(vax['file'], pages=pages, pandas_options={'header': None}, multiple_tables=True, stream=True, silent=True)
    print('Ho letto.')

    # Unisci in un unico dataframe e bonifica i dati
    vax = pd.concat(pdf).reset_index(drop=True)
    vax = vax.dropna(thresh=3)
    vax = vax[~vax[0].str.contains("Provincia", na=False)]
    vax.drop(vax.columns[[0]], axis=1, inplace=True)

    for index, row in vax.iterrows():
        if(pd.isnull(row[2])):
            row[2] = row[3]
            row[3] = row[4]

    vax.reset_index(drop=True, inplace=True)
    vax.drop(vax.columns[3], axis=1, inplace=True)
    vax.columns = ['comune', '%vaccinati', '%immunizzati']

    # Carica l'helper comuni siciliani
    out = pd.merge(vax, comuni, on='comune', how='inner')
    out = out[['cod_prov', 'pro_com_t', 'provincia','comune', '%vaccinati', '%immunizzati']]
    out['%vaccinati'] = out['%vaccinati'].str.replace(',', '.').str.rstrip('%')
    out['%immunizzati'] = out['%immunizzati'].str.replace(',', '.').str.rstrip('%')
    out.insert(0, 'data', date)

    assert (len(out) == 390), "Errore: Sono presenti meno comuni del previsto."
   
    # Esporta CSV
    print('Esporto CSV...')
    out.to_csv(path+'/dati-csv/vaccini/vaccini-'+date.replace("-", "")+'.csv', index=None, header=True)
    out.to_csv(path+'/dati-csv/vaccini/vaccini-latest.csv', index=None, header=True)
    out.to_csv(path+'/dati-csv/vaccini/vaccini.csv', mode='a', index=None, header=False)
    csv = path+'/dati-csv/vaccini/vaccini-'+date.replace("-", "")+'.csv'

    return csv


def getIncidenza(pdf):
    '''
    Estrae l'incidenza da file PDF
    '''
    print('Leggo tabella Incidenza...attendi...')
    reader = PdfFileReader(pdf['file'])
    pages = pdf['incidenza']

    textes = []
    try:
        for i in range(pages[0], pages[-1]+1):
            page = reader.getPage(i)
            text = page.extractText()
            text = text.replace('\n', ' ')
            textes.append(text[2::])
    except Exception as e:
        print(e)

    out = ' '.join(textes)\
        .rpartition('settimane')[2]\
        .rpartition('Totale')[0]\
        .replace('- ', '-')\
        .replace('---', '0%')\
        .replace('  ', ' ')\
        .replace('  ', ' ')\
        .replace('  ', ' ')\
        .replace('%', '')\
        .replace("O'", "Ò").replace("I'", "Ì").replace("U'", "Ù")\
        .split()

    new = ""
    for split in out:
        if not isDigit(split):
            new = new + split + ' '
        if isDigit(split):
            new = new + ',' + split + ','
    new = new.replace(',,', ',').replace(
        ' ,', ',').replace(' -', '-').split(',')

    it = iter(new)
    data = list(zip(it, it, it, it))

    df = pd.DataFrame(data, columns=['comune', 'casi', 'incidenza', 'variazione'])
    df = df[['comune', 'incidenza', 'casi']]

    incidenza = df[~df["comune"].duplicated(keep="last")]
    incidenza.reset_index(inplace=True, drop=True)

    out = pd.merge(incidenza, comuni, left_on=incidenza["comune"].str.lower(), right_on=comuni["comune"].str.lower(), how="inner")
    out.rename(columns={'comune_y': 'comune'}, inplace=True)
    out = out[['cod_prov', 'pro_com_t', 'provincia', 'comune', 'incidenza', 'casi']].sort_values(by=['provincia', 'comune'])
    out.reset_index(drop=True, inplace=True)
    out.insert(0, 'data', date)

    assert (len(out) == 390), "Errore: Sono presenti meno comuni del previsto."

    # Esporta CSV
    print('Esporto CSV...')
    out.to_csv(path+'/dati-csv/incidenza/incidenza-'+date.replace("-", "")+'.csv', index=None, header=True)
    out.to_csv(path+'/dati-csv/incidenza/incidenza-latest.csv', index=None, header=True)
    out.to_csv(path+'/dati-csv/incidenza/incidenza.csv', mode='a', index=None, header=False)
    csv = path+'/dati-csv/incidenza/incidenza-'+date.replace("-", "")+'.csv'

    return csv


getIncidenza(getRanges(path+'/download/'+latest['nome_file']))
getVax(getRanges(path+'/download/'+latest['nome_file']))

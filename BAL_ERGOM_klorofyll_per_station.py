#!/usr/bin/pyhton3
# 
# Baltic Sea Biogeochemistry Reanalysis
# Extrahera klorofyll för valda stationer
#
# Användning:
# python3 BAL_ERGOM_klorofyll_per_station.py
# 
# Behöver Copernicus ERGOM NetCDF data
# 
# *** THIS IS WORK IN PROGRESS ***
# 
# 2023-05-15
# 
# Hernán De Angelis, HaV/GeoNatura

import re
import sys
import os
from datetime import date
from datetime import datetime as DT

from osgeo import gdal 
import numpy as np
import math
import matplotlib
import matplotlib.pyplot as plt
    
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# grundparametrarna, anpassa vid behov

# lokaladress till datarepo
data_dir = '/home/hernan/arkiv/datos/ambiente/CMEMS_MY/BAL-MYP-ERGOM_BGC-AnnualMeans'

# Stationsregistrets WFS
stnreg_wfs_adress = 'https://stationsregister.miljodatasamverkan.se/geoserver/stationsregistret/wfs?'
stnreg_wfs_featurename = 'stationsregistret:active_site'
stnreg_wfs_version = '1.1.0'

# dagens datum
idag = date.today()

# arbetsmapp
cwd = os.getcwd()

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# plocka koordinater för varje station enligt site_id i Stationsregistret
stationList = (
    '135660',
    '135611',
    '135420',
    '180822',
    )

# lexikon för att samla koordinaterna och namn
stationLexikon = {}

# importera modul för POST frågor
import requests

for station in stationList:
    # print(station)

    # bygg WFS frågan
    wfsRequest = f"""<?xml version="1.0" encoding="UTF-8"?><wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="{stnreg_wfs_version}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/2.0.0/WFS-transaction.xsd">
        <wfs:Query typeName="{stnreg_wfs_featurename}" xmlns:feature="http://lst.se/gde" srsName="EPSG:4326">
            <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
                <ogc:PropertyIsEqualTo>
                    <ogc:PropertyName>site_id</ogc:PropertyName>
                    <ogc:Literal>{station}</ogc:Literal>
                </ogc:PropertyIsEqualTo>
            </ogc:Filter></wfs:Query>
        </wfs:GetFeature>"""

    # skicka WFS request
    header = {'Content-type':'application/xml', 'encoding':'UTF-8'}
    wfsResponse = requests.post(stnreg_wfs_adress, data=wfsRequest.encode('utf-8'), headers=header)
    
    # spara respons som text
    wfsResponseText = wfsResponse.text
    # print(wfsResponseText)

    # parsa koordinaterna
    from xml.etree import ElementTree
    
    # läs GML trä
    try:
        global tree
        tree = ElementTree.fromstring(wfsResponseText)
    except NameError:
        print('Fel NameError')
    except Exception:
        print('Fel Exception')
    except AttributeError:
        print('Fel AttributeError')

    for elem in tree.iter('{http://www.opengis.net/wfs}FeatureCollection'):
        # position
        positionRAW = elem.find(".//{http://www.opengis.net/gml}pos")
        positionREN = (positionRAW.text)
        nameRAW = elem.find(".//{http://miljodatasamverkan.se/so/ef/environmentalmonitoringfacility}name")
        nameREN = (nameRAW.text)
        # print(positionREN, nameREN)
        
        # spara i lexikonet
        stationLexikon[station] = f"{positionREN} {nameREN}"
        


# samla en lista över alla datamängder
fileList = os.listdir(data_dir)
fileList.sort()

# för varje station i lexikonet, plocka relevant värde från varje datamängd
for station in stationLexikon:
    attributLista = stationLexikon[station].split()
    stationLon = attributLista[0]
    stationLat = attributLista[1]
    stationNmn = attributLista[2]
    print (stationLon, stationLat, stationNmn)

    # öppna tom lista för värden
    varden = []

    # fånga värdet av klorofyll i angivna koordinaterna
    for filenc in fileList:
        # hoppa över om inte en nc fil
        if re.search("aux.xml", filenc):
            break
        # print(filenc)
    
        # läs datamängd
        dataset = gdal.Open("NETCDF:{0}:{1}".format(data_dir+'/'+filenc, 'chl'))
                
        def get_raster_value(geo_x: float, geo_y: float, ds: gdal.Dataset, band_index: int = 1):
            """Return raster value that corresponds to given coordinates."""
            forward_transform = ds.GetGeoTransform()
            reverse_transform = gdal.InvGeoTransform(forward_transform)
            pixel_coord = gdal.ApplyGeoTransform(reverse_transform, geo_x, geo_y)
            pixel_x = math.floor(pixel_coord[0])
            pixel_y = math.floor(pixel_coord[1])
            band: gdal.Band = ds.GetRasterBand(band_index)
            val_arr = band.ReadAsArray(pixel_x, pixel_y, 1, 1) # Avoid reading the whole raster into memory - read 1x1 array
            return val_arr[0][0]
    
        varden.append(get_raster_value(float(stationLon), float(stationLat), dataset, 1))
    
    # plottar

    # testar
    # print(varden)

    # quick & dirty nu, ska ersättas för en läsare för metadata
    aren = [*range(1993, 2022, 1)]
    
    plt.plot(aren, varden)
    plt.xlabel('År')
    plt.ylabel('Klorofyll [mg m-3]')
    plt.title(f"""Klorofyll för {stationNmn} (Lon: {stationLon}, Lat: {stationLat}) \n Copernicus ERGOM data""")
    plt.savefig('klorofyll_'+stationNmn+'.png')
    plt.close()
    

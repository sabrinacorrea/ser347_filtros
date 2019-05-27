"""
        Trabalho Final SER347
Autores:                    Arian Carneiro
                            Leandro Lanes
                            Sabrina Correa.
Data de criação:            03/05/2019
Data da última modificação: 27/05/2019

Descrição: Script em Python 3 para realizar filtragens SAR em 3 janelas distintas.
"""
# ======================================================================================================================
# IMPORTANDO BIBLIOTECAS
# ======================================================================================================================

import os, errno, csv
from osgeo import gdal, osr
from scipy.ndimage.filters import uniform_filter, median_filter
from scipy.ndimage.measurements import variance
import tkinter as tk
from tkinter import filedialog
import numpy as np
 
# Informando o uso de exceções
gdal.UseExceptions()


# ======================================================================================================================
# 1 - CRIAÇÃO DE FUNÇÕES
# ======================================================================================================================

# Criando uma função para o Filtro de Lee
def filtro_lee (img, size):
    img_mean = uniform_filter(img, (size, size))
    img_sqr_mean = uniform_filter(img**2, (size, size))
    img_variance = img_sqr_mean - img_mean**2

    overall_variance = variance(img)

    img_weights = img_variance / (img_variance + overall_variance)
    img_output = img_mean + img_weights * (img - img_mean)
    return img_output

# Criando uma função para o Filtro de Mediana
def filtro_mediana (img, size):
    img_median = median_filter(img, (size, size))
    return img_median

# Criando uma função para o Filtro de Média
def filtro_media (img, size):
    img_mean = uniform_filter(img, (size, size))
    return img_mean

# Criando uma função para escrever o dado de saída.
def salvar_banda(matriz_de_pixels, nome_do_arquivo, dataset_de_referencia):
    # obter metadados
    linhas = dataset_de_referencia.RasterYSize
    colunas = dataset_de_referencia.RasterXSize
    bandas = 1
    # definir driver
    driver = gdal.GetDriverByName('GTiff')
    # copiar tipo de dados da banda já existente
    data_type = dataset_de_referencia.GetRasterBand(1).DataType
    # criar novo dataset
    dataset_output = driver.Create(nome_do_arquivo, colunas, linhas, bandas, data_type)
    # copiar informações espaciais da banda já existente
    dataset_output.SetGeoTransform(dataset_de_referencia.GetGeoTransform())
    # copiar informações de projeção
    dataset_output.SetProjection(dataset_de_referencia.GetProjectionRef())
    # escrever dados da matriz NumPy na banda
    dataset_output.GetRasterBand(1).WriteArray(matriz_de_pixels)
    # salvar valores
    dataset_output.FlushCache()
    # fechar dataset
    dataset_output = None

# Função de cálculo de estatísticas
def stats_sar(img_ori, img_filt):
    # Erro médio quadrático (Mean Square Error - MSE)
    MSE = ((img_filt - img_ori)**2)
    MSE = MSE.mean()
    # Relação Sinal-Ruido (Signal to Noise Ratio - SNR)
    SNR_original = img_ori.mean()/img_ori.std()
    SNR_filtrado = imgfiltrada.mean()/imgfiltrada.std()
    return [MSE, SNR_original, SNR_filtrado]

# Criação de matriz das estatísticas vazia:
#   Este numpy array foi criado para que sejam feito um "append" dos valores da estatistica dos dados
estatistica = [[0,0,0]]
parametros = [[0, 0, 0]]
# ======================================================================================================================
# 2 - ENTRADA E VERIFICAÇÃO DE DADOS
# ======================================================================================================================

# Definindo Variaveis (Diretorios no Ubuntu, para verificar, usar os.getcwd())

janela_aplicacao = tk.Tk()

# Perguntar ao usuário para selecionar um diretório
dir_entrada = filedialog.askdirectory(parent=janela_aplicacao, initialdir=os.getcwd(),  title="Selecione um diretório:")
# Criando um diretorio dentro do selecionado chamado "saida" e determinando que o programa exportatá os dados todos para este diretório
dir_saida = (dir_entrada + '/saida')
# Testando para saber se o diretorio já é existente
#   Corrigindo erro 17 para mkdir
try:
    os.mkdir(dir_entrada + '/saida')
except OSError as exc:
    print("Diretorio já existente")
    if exc.errno != errno.EEXIST:
        raise
    pass

#Mudando o diretorio de estudo
os.chdir(dir_saida)

print(f'o diretório de entrada de dados é: {dir_entrada}.')
print(f'o diretório de saida de dados é: {dir_saida}.')

print('\nAs cenas serão filtradas em 3 janelas: 3x3, 5x5 e 7x7.'
      ' Todas serão avaliadas quanto sua relação sinal-ruído.')

# Criando uma lista contendo os apenas arquivos TIFF do diretório de entrada
lista_entrada1 = os.listdir(dir_entrada)
lista_entrada = []
for arquivo in lista_entrada1:
    if arquivo.endswith(".tif"):
        lista_entrada.append(arquivo)

# Imprimindo lista para ver que arquivos a compõem
print(f'\n{lista_entrada}\n')

filter = input('\nInsira o filtro para aplicar nas cenas'
               '\n(1) -> Lee'
               '\n(2) -> Mediana'
               '\n(3) -> Media: ')

# Contador para numero de imagens listadas
cont = 0
# Verificação dos arquivos
for ii in lista_entrada:

    if os.path.isfile(dir_entrada + '/' + ii):
        arqsext = os.path.splitext(ii)[0]
        pathabs = gdal.Open(dir_entrada + '/' + ii, gdal.GA_ReadOnly)  
        imagem_original = pathabs.ReadAsArray()
        # Avaliando os parâmetros do dado aberto
        print(f"\nA imagem {ii} possui os seguintes parâmetros:")
        print("Formato: {}/{}".format(pathabs.GetDriver().ShortName,
                                      pathabs.GetDriver().LongName))
        print("Tamanho: {} x {} pixels e {} banda(s)".format(pathabs.RasterXSize,
                                                             pathabs.RasterYSize,
                                                             pathabs.RasterCount))
        print("LatLong_Inicial: {} {}\nRes(x,y): {} {}".format(pathabs.GetGeoTransform()[3],
                                                               pathabs.GetGeoTransform()[0],
                                                               pathabs.GetGeoTransform()[1],
                                                               pathabs.GetGeoTransform()[5]))
        banda = pathabs.GetRasterBand(1)
        print("Tipo de dado: {}".format(gdal.GetDataTypeName(banda.DataType)))
        
        prj = pathabs.GetProjection()
        srs = osr.SpatialReference(wkt = prj)

        if srs.IsProjected:
            print('Projeção:', srs.GetAttrValue('projcs'))
            print('Datum:', srs.GetAttrValue('geogcs'), '\n')
        else:
            print('A imagem não possui referência espacial!\n')

        # ======================================================================================================================
        # 3 - APLICAÇÃO DE FILTROS
        # ======================================================================================================================

        # Filtro Lee
        if filter == '1':
            for i in range (3, 8, 2):
                lee = dir_saida + "/" + arqsext + "_Lee" + f'_{i}X{i}' + ".tif"
                filtro = "Lee"
                imgfiltrada = filtro_lee(pathabs.ReadAsArray(), i)
                salvar_banda(imgfiltrada, lee, pathabs)
                [MSE, SNR_ori, SNR_filt] = stats_sar(imagem_original, imgfiltrada)
                estatistica = np.append(estatistica, [[MSE, SNR_ori, SNR_filt]], axis=0)
        # Filtro Mediana
        elif filter == '2':
            for i in range (3, 8, 2):
                median = dir_saida + "/" + arqsext + "_Median" + f'_{i}X{i}' + ".tif"
                filtro = "Mediana"
                imgfiltrada = filtro_mediana(pathabs.ReadAsArray(), i)
                salvar_banda(imgfiltrada, median, pathabs)
                [MSE, SNR_ori, SNR_filt] = stats_sar(imagem_original, imgfiltrada)
                estatistica = np.append(estatistica, [[MSE, SNR_ori, SNR_filt]], axis=0)
        # Filtro Média
        elif filter == '3':
            for i in range(3, 8, 2):
                mean = dir_saida + "/" + arqsext + "_Mean" + f'_{i}X{i}' + ".tif"
                filtro = "Media"
                imgfiltrada = filtro_media(pathabs.ReadAsArray(), i)
                salvar_banda(imgfiltrada, mean, pathabs)
                [MSE, SNR_ori, SNR_filt] = stats_sar(imagem_original, imgfiltrada)
                estatistica = np.append(estatistica, [[MSE, SNR_ori, SNR_filt]], axis=0)
        # Else
        else:
            print('caractere invalido!')

    cont += 1

# ======================================================================================================================
# 4 - IMPRIMINDO RESULTADOS
# ======================================================================================================================
cont = len(lista_entrada)
mascara = ("0","3x3", "5x5", "7x7")
with open("estatistica.csv", "w", newline='') as csvfile:
    filewriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    filewriter.writerow(["Imagem", "Filtro", "Mascara", "MSE", "SNR Img Origem", "SNR Img Filtrada"])
    for i in range(cont):
        for j in range(1,4):
            filewriter.writerow([lista_entrada[i], filtro, mascara[j], estatistica[j][0], estatistica[j][1], estatistica[j][2]])

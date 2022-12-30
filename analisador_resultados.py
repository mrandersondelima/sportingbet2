import os
from time import sleep
from telegram_bot import TelegramBot
from credenciais import path_to_results
#from app import AnalisadorResultados
from datetime import datetime
import subprocess

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

array_resultados = []
NUMERO_JOGOS_AMARELOS = 6
numero_jogos_amarelos_atual = 0
ultimo_jogo = dict()
telegram_bot = TelegramBot()
atingiu_jogos_amarelos = False
atingiu_jogos_amarelos_anterior = 0
primeira_execucao = True
pausa_menor = False
vinte_ultimos_amarelos = 0
vinte_ultimos_verdes = 0

ultima_lista = ''

# a cada 20 jogos o sistema vai emitir um alerta avisando que ainda está rodando
contador_jogos = 0

def verifica_lista( lista_resultados, ultima_lista ):
    if ultima_lista == '':
        return False
    else:
        if ultima_lista[4::] in lista_resultados:
            return False
        else:
            return True

def pega_ultimo_resultado():
    try:
        saida = subprocess.Popen(f'{path_to_results}').read()
        if saida.split('\n')[0] == '' or 'PLAYNOW!' not in saida:
            pass
        else:
            lista_resultados = saida.split('\n')[2]

            if '_' not in lista_resultados:
                pausa_menor = False
                # essa lista já foi capturado
                if ultimo_jogo.get(lista_resultados) == True:
                    pass
                else:
                    resultados = lista_resultados.split(' ')

                    gols_casa = int(resultados[0].split('x')[0])
                    gols_fora = int(resultados[0].split('x')[1])
                    return gols_casa + gols_fora
                
                if len(ultimo_jogo) == 2:
                    del ultimo_jogo[ultima_lista]
                # adiciona a nova lista no dicionário
                ultimo_jogo[lista_resultados] = True         
            else:
                pausa_menor = True
                sleep(5)
        if not pausa_menor:
            sleep(15)
    except Exception as e:
        print(e)

def ler_resultados():

    analisar_apenas = int(input('USAR APENAS COMO ANALISADOR? (1) SIM (2) NÃO'))
    if analisar_apenas == 1:
        analisar_apenas = True
    else:
        analisar_apenas = False

    n_jogos_amarelos = 0
    n_jogos_verdes_em_sequencia = 0
    primeira_execucao = True
    ultimo_foi_verde = False
    while True:
        pausa_menor = False
        try:
            saida = os.popen(f'{path_to_results}').read()
            if saida.split('\n')[0] == '' or 'PLAYNOW!' not in saida:
                pass
            else:
                lista_resultados = saida.split('\n')[2]

                if '_' not in lista_resultados:
                    pausa_menor = False
                    # essa lista já foi capturado
                    if ultimo_jogo.get(lista_resultados) == True:
                        pass
                    else:
                        print(lista_resultados)
                        print( datetime.now().strftime('%d/%m/%Y %H:%M') )

                        #verifica se a lista é imediatamente subsequente ou se há quebra...
                        #lista_quebrada = verifica_lista( lista_resultados, ultima_lista )

                        #if lista_quebrada:
                        #    primeira_execucao = True
                        #    numero_jogos_amarelos_atual = 0

                        resultados = lista_resultados.split(' ')

                        if primeira_execucao:
                            primeira_execucao = False
                            array_resultados = []
                            n_jogos_amarelos = 0
                            n_jogos_verdes_em_sequencia = 0
                            ultimo_foi_verde = False
                            for placar in resultados:
                                gols_casa = placar.split('x')[0]
                                gols_fora = placar.split('x')[1]
                                if int(gols_casa) + int(gols_fora) < 3:
                                    array_resultados.append(f"{bcolors.WARNING}⬤{bcolors.ENDC} ")
                                else:
                                    array_resultados.append(f"{bcolors.OKGREEN}⬤{bcolors.ENDC} ")

                        else:
                            gols_casa = int(resultados[0].split('x')[0])
                            gols_fora = int(resultados[0].split('x')[1])
                            if int(gols_casa) + int(gols_fora) < 3:
                                if not ultimo_foi_verde:
                                    n_jogos_amarelos += 1
                                n_jogos_verdes_em_sequencia = 0
                                ultimo_foi_verde = False
                                array_resultados.insert(0,f"{bcolors.WARNING}⬤{bcolors.ENDC} ")
                            else:
                                array_resultados.insert(0,f"{bcolors.OKGREEN}⬤{bcolors.ENDC} ")
                                if not ultimo_foi_verde:
                                    n_jogos_amarelos += 1
                                ultimo_foi_verde = True
                                n_jogos_verdes_em_sequencia += 1
                            
                            if n_jogos_amarelos >= 20:
                                    telegram_bot.envia_mensagem(f'{n_jogos_amarelos} JOGOS AMARELOS')
                                    if not analisar_apenas:
                                        subprocess.Popen(['python', 'C:\\Users\\anderson.morais\\Documents\\dev\\sportingbet\\app.py', '14', '1', '2.5', '1', '5', '1', '2', '1'])
                                        primeira_execucao = True

                            if n_jogos_verdes_em_sequencia == 3:
                                telegram_bot.envia_mensagem(f'TRÊS VERDES DEPOIS DE {n_jogos_amarelos - 1} JOGOS AMARELOS')
                                n_jogos_verdes_em_sequencia = 0
                                n_jogos_amarelos = 0
                                ultimo_foi_verde = False

                        if len(ultimo_jogo) == 2:
                            del ultimo_jogo[ultima_lista]
                        # adiciona a nova lista no dicionário
                        ultimo_jogo[lista_resultados] = True         

                        ultima_lista = lista_resultados   

                        if len(array_resultados) == 70:
                            array_resultados.pop()

                        for resultado in array_resultados:
                            print(resultado, end='', flush=True)
                        print()
                else:
                    pausa_menor = True
                    sleep(5)
            if not pausa_menor:
                sleep(15)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    ler_resultados()
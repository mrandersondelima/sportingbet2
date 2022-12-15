import os
from time import sleep
from telegram_bot import TelegramBot
from credenciais import path_to_results
from app import AnalisadorResultados

NUMERO_JOGOS_AMARELOS = 6
numero_jogos_amarelos_atual = 0
ultimo_jogo = dict()
telegram_bot = TelegramBot()
atingiu_jogos_amarelos = False
primeira_execucao = True
pausa_menor = False

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

while True:
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
                    print('Nova lista: ', lista_resultados)

                    contador_jogos += 1

                    if contador_jogos % 10 == 0:
                        telegram_bot.envia_mensagem(f'Sistema ainda rodando...')

                    #verifica se a lista é imediatamente subsequente ou se há quebra...
                    lista_quebrada = verifica_lista( lista_resultados, ultima_lista )

                    if lista_quebrada:
                        primeira_execucao = True
                        numero_jogos_amarelos_atual = 0

                    resultados = lista_resultados.split(' ')

                    if primeira_execucao:
                        primeira_execucao = False
                        for placar in resultados:
                            gols_casa = placar.split('x')[0]
                            gols_fora = placar.split('x')[1]
                            if int(gols_casa) + int(gols_fora) < 3:
                                numero_jogos_amarelos_atual += 1
                            else:
                                break
                    else:
                        gols_casa = int(resultados[0].split('x')[0])
                        gols_fora = int(resultados[0].split('x')[1])
                        if int(gols_casa) + int(gols_fora) < 3:
                            numero_jogos_amarelos_atual += 1
                        else:
                            numero_jogos_amarelos_atual = 0
                            if atingiu_jogos_amarelos:
                                telegram_bot.envia_mensagem(f'JANELA DE APOSTA FECHADA.')
                                atingiu_jogos_amarelos = False

                    print(numero_jogos_amarelos_atual)

                    if numero_jogos_amarelos_atual >= NUMERO_JOGOS_AMARELOS:
                        telegram_bot.envia_mensagem(f'HORA DE APOSTAR!!! {numero_jogos_amarelos_atual} JOGOS.')

                        #aqui entra toda a lógica da aposta

                        analisador = AnalisadorResultados(n_amarelos=numero_jogos_amarelos_atual)
                        analisador.aposta()

                        atingiu_jogos_amarelos = True
                        primeira_execucao = True

                    if len(ultimo_jogo) == 2:
                        del ultimo_jogo[ultima_lista]
                    # adiciona a nova lista no dicionário
                    ultimo_jogo[lista_resultados] = True         

                    ultima_lista = lista_resultados   
            else:
                pausa_menor = True
                sleep(5)
        if not pausa_menor:
            sleep(15)
    except Exception as e:
        print(e)


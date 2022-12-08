from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from time import sleep
import pause
import json
from datetime import datetime, timedelta
from credenciais import usuario, senha
from telegram_bot import TelegramBot
from random import randrange
import os
from utils import *

hora_jogo_atual = None
meta_atingida = False

# armazena a porcentagem de acordo com o número de jogos amarelos
n_amarelos_e_porcentagem = [0, 0, 0, 0, 0, 0, 0, 1.0, 1.8, 3.3, 6, 11, 21]

class ChromeAuto():
    def __init__(self, meta=0, tipo_valor=1, valor_aposta=None, tipo_meta=None, estilo_jogo=None, ao_atingir_meta=None):
        self.driver_path = 'chromedriver'
        self.options = webdriver.ChromeOptions()
        self.chrome = webdriver.Chrome(self.driver_path)
        self.valor_aposta = valor_aposta
        self.valor_aposta_inicial = valor_aposta
        self.meta = float(meta)
        self.meta_inicial = float(meta)
        self.saldo = 0
        self.saldo_inicial = 0
        self.saldo_antes_aposta = 0
        self.tipo_valor = tipo_valor
        self.estilo_jogo = estilo_jogo
        self.estilo_rodada = None
        self.tipo_meta = tipo_meta
        self.aposta_fechada = False
        self.telegram_bot = TelegramBot()
        self.array_randomico = self.gera_array_randomico()
        self.perda_acumulada = 0.0
        self.controle_frequencia_mensagens = 0
        self.jogos_realizados = dict()
        self.hora_jogo = ''
        self.contador_perdas = 0
        self.perdidas_em_sequencia = 0
        self.maior_perdidas_em_sequencia = 0
        self.ao_atingir_meta = ao_atingir_meta
        return

    def acessa(self, site):
        self.chrome.get(site)
        self.chrome.maximize_window()

    def sair(self):
        self.chrome.quit()

    def clica_sign_in(self):
        sleep(2)
        try:
            elem = WebDriverWait(self.chrome, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="https://www.sportingbet.com/pt-br/labelhost/login"]' )  )) 
            elem.click()
        except Exception as e:
            print(e)

    def faz_login(self):
        try:
            input_login = WebDriverWait(self.chrome, 10).until(
                EC.element_to_be_clickable((By.ID, 'userId' )  )) 
            input_login.send_keys(usuario)         
            
            input_password = WebDriverWait(self.chrome, 10).until(
                EC.element_to_be_clickable((By.NAME, 'password' )  )) 
            input_password.send_keys(senha)

            botao_login = WebDriverWait(self.chrome, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[class="login w-100 btn btn-primary"]' )  )) 
            sleep(2)
            botao_login.click()

            sleep(4)

            self.le_saldo()
            print(f'SALDO ATUAL: {self.saldo}')

            # saldo inicial não pode ser alterado ao longo de toda uma rodada
            self.saldo_inicial = self.saldo

            self.atualiza_meta_e_valor_aposta()

            print(f'VALOR POR APOSTA: {self.valor_aposta:.2f}')        
            print(f'META: { self.meta:.2f}')
            self.telegram_bot.envia_mensagem(f'SALDO ATUAL: {self.saldo}\nVALOR POR APOSTA: {self.valor_aposta:.2f}\nMETA: { self.meta:.2f}')

            sleep(2)
            self.chrome.execute_script('document.getElementById("main-view").scrollIntoView()')
            sleep(2)

            cookies = WebDriverWait(self.chrome, 20).until(
                EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler' ) )) 
            cookies.click() 
        except Exception as e:
            print(e)

    def atualiza_meta_e_valor_aposta(self):
        ''' tanto a meta quanto o valor são percentuais '''
        if self.tipo_meta == TipoMeta.PORCENTAGEM and self.tipo_valor == TipoValorAposta.PORCENTAGEM:
            self.valor_aposta = self.saldo * ( self.valor_aposta_inicial / 100 )
            self.meta = self.saldo + self.saldo * ( self.meta_inicial / 100 )
        elif self.tipo_meta == TipoMeta.VALOR_ABSOLUTO and self.tipo_valor == TipoValorAposta.PORCENTAGEM:
            ''' meta é absoluta e valor é percentual '''
            self.valor_aposta = self.saldo * ( self.valor_aposta_inicial / 100 )
            ''' meta é percentual e valor é absoluto '''
        elif self.tipo_meta == TipoMeta.PORCENTAGEM and self.tipo_valor == TipoValorAposta.VALOR_ABSOLUTO:
            self.meta = self.saldo + self.saldo * ( self.meta_inicial / 100 )
        elif self.tipo_meta == TipoMeta.SALDO_MAIS_META and self.tipo_valor == TipoValorAposta.PORCENTAGEM:
            self.meta = self.saldo + self.valor_aposta
            self.valor_aposta = self.saldo * ( self.valor_aposta_inicial / 100 )
        elif self.tipo_meta == TipoMeta.SALDO_MAIS_META and self.tipo_valor == TipoValorAposta.VALOR_ABSOLUTO:
            self.meta = self.saldo + self.valor_aposta   
        elif self.tipo_meta == TipoMeta.SALDO_MAIS_VALOR and self.tipo_valor == TipoValorAposta.PORCENTAGEM:       
            self.valor_aposta = self.saldo * ( self.valor_aposta_inicial / 100 )
            self.meta = self.saldo + self.meta
        elif self.tipo_meta == TipoMeta.SALDO_MAIS_VALOR and self.tipo_valor == TipoValorAposta.VALOR_ABSOLUTO:
            self.meta = self.saldo + self.meta

    def clica_horario_jogo(self, horario_jogo):
        print('Entrou no clica_horario_jogo')
        try:
            horario = WebDriverWait(self.chrome, 10).until(
                EC.element_to_be_clickable((By.XPATH, horario_jogo)))
            horario.click()
            sleep(2)
            horario.click()
            sleep(2)

            # aqui vai ver se tem o mercado de resultado do jogo            
            resultado_partida =  WebDriverWait(self.chrome, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[normalize-space(text()) = 'Resultado da partida']")))

        except Exception as e:
            ''' aqui a gente verifica se o item atual tem sibling, 
            se tiver é porque o horário não existe, então passamos pro próximo horário '''   
            print(e)
            print('Algo saiu errado no clica_horario_jogo')
            self.aposta_fechada = True             

    def insere_valor(self, valor):
        print('Entrou no insere_valor')
        contador_travamento = 0
        while True:         
            contador_travamento += 1
            if self.estilo_rodada == EstiloJogo.FAVORITO_COM_ODD_MAIOR_IGUAL_2 or \
                self.estilo_rodada == EstiloJogo.FAVORITO_COM_ODD_MENOR_1_E_MEIO or \
                self.estilo_rodada == EstiloJogo.JOGO_UNICO_ODD_ABAIXO_2_MEIO or \
                self.estilo_rodada == EstiloJogo.JOGO_UNICO_ODD_ACIMA_2_MEIO:
                try:
                    input_valor = WebDriverWait(self.chrome, 20).until(
                            EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[2]/div/div/div/div/ms-widget-column/ms-widget-slot/ms-bet-column/ms-betslip-component/div/div[2]/div/ms-betslip-stakebar/div/div/span/ms-stake/div/ms-stake-input/div/input') )) 
                    sleep(2)
                    input_valor.clear()
                    input_valor.send_keys(valor)
                except Exception as e:
                    print(e)
                    print('Algo saiu errado no insere_valor')
            elif self.estilo_rodada == EstiloJogo.ZEBRA_COM_ODD_MAIOR_IGUAL_2 or \
                self.estilo_rodada == EstiloJogo.FAVORITO_EMPATE_COM_ODD_MAIOR_IGUAL_2 or \
                self.estilo_rodada == EstiloJogo.RANDOMICO_ENTRE_JOGO_2_E_5 or \
                self.estilo_rodada == EstiloJogo.TOTAL_GOLS or \
                self.estilo_rodada == EstiloJogo.DOIS_GOLS_OU_ABAIXO_1_E_MEIO:
                input_valor = WebDriverWait(self.chrome, 20).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[2]/div/div/div/div/ms-widget-column/ms-widget-slot/ms-bet-column/ms-betslip-component/div/div[1]/div[1]/ms-betslip-picks/div[1]/div[1]/ms-betslip-v1-pick/div[2]/div/div/div[2]/div/div[2]/div[2]/div/ms-stake/div/ms-stake-input/div/input') )) 
                input_valor.clear()
                input_valor.send_keys(valor)

                sleep(2)

                input_valor_2 = WebDriverWait(self.chrome, 20).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[2]/div/div/div/div/ms-widget-column/ms-widget-slot/ms-bet-column/ms-betslip-component/div/div[1]/div[1]/ms-betslip-picks/div[1]/div[2]/ms-betslip-v1-pick/div[2]/div/div/div[2]/div/div[2]/div[2]/div/ms-stake/div/ms-stake-input/div/input') )) 
                input_valor_2.clear()
                input_valor_2.send_keys(valor)   

            sleep(2)

            try:
                botao_aposta = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[2]/div/div/div/div/ms-widget-column/ms-widget-slot/ms-bet-column/ms-betslip-component/div/div[2]/div/div/ms-betslip-action-button/div/button' ) )) 
                botao_aposta.click()     

                sleep(2) 

                botao_fechar = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[2]/div/div/div/div/ms-widget-column/ms-widget-slot/ms-bet-column/ms-betslip-component/div/div/div/div/button' ) )) 
                botao_fechar.click() 

                sleep(2)

                self.jogos_realizados[self.hora_jogo] = True

                print('JOGOS REALIZADOS:', len(self.jogos_realizados))

                self.le_saldo()

                print(f'SALDO ATUAL: {self.saldo}')
                print(f'META: {self.meta:.2f}')

                numero_apostas_abertas = self.chrome.execute_script(f'let d = await fetch("https://sports.sportingbet.com/pt-br/sports/api/mybets/betslips?index=1&maxItems=12&typeFilter=2"); return await d.json();')
                numero_apostas_abertas = numero_apostas_abertas['summary']['openBetsCount']

                if numero_apostas_abertas == 1:
                    break

                if contador_travamento == 10:
                    self.telegram_bot.envia_mensagem(f'SISTEMA POSSIVELMENTE TRAVADO!!!')

            except Exception as e:
                lixeira = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[2]/div/div/div/div/ms-widget-column/ms-widget-slot/ms-bet-column/ms-betslip-component/div/div[1]/div[1]/ms-betslip-picks/div[2]/ms-betslip-remove-all-picks/div/div' ) )) 
                lixeira.click()
                confirmacao_exclusao = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[2]/div/div/div/div/ms-widget-column/ms-widget-slot/ms-bet-column/ms-betslip-component/div/div[1]/div[1]/ms-betslip-picks/div[2]/ms-betslip-remove-all-picks/div' ) )) 
                confirmacao_exclusao.click()
                print(e)
                print('Algo saiu errado no insere_valor')

    def analisa_odds(self):
        print('Entrou no analisa_odds')
        try: 
            resultado_final = WebDriverWait(self.chrome, 5).until(
                    EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-option-panel-header/div/div/div/div') )) 
            ''' o único mercado que importa é o resultado final '''
            if resultado_final.get_property("innerText") == 'Resultado da partida':
                odd_casa = WebDriverWait(self.chrome, 20).until(
                    EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[1]/ms-event-pick/div/div[2]') )) 

                odd_casa = odd_casa.get_property('innerText')
                odd_empate = WebDriverWait(self.chrome, 20).until(
                    EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[2]/ms-event-pick/div/div[2]') )) 

                odd_empate = odd_empate.get_property('innerText')
                odd_fora = WebDriverWait(self.chrome, 20).until(
                    EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[3]/ms-event-pick/div/div[2]') )) 

                odd_fora = odd_fora.get_property('innerText')

                odd_casa = float(odd_casa)
                odd_empate = float(odd_empate)
                odd_fora = float(odd_fora)

                if self.estilo_jogo == EstiloJogo.ALEATORIO_COM_ODD_MAIOR_IGUAL_2:
                    self.estilo_rodada = randrange(2) + 1
                elif self.estilo_jogo == EstiloJogo.RANDOMICO_ENTRE_JOGO_2_E_5:
                    jogos = [2, 5]
                    self.estilo_rodada = jogos[ self.array_randomico.pop(0) ]
                else:
                    self.estilo_rodada = self.estilo_jogo

                if self.estilo_rodada == EstiloJogo.FAVORITO_COM_ODD_MAIOR_IGUAL_2:

                    if odd_casa >= 3.00 and odd_empate >= 3.00 and odd_fora >= 2:

                            aposta_fora = WebDriverWait(self.chrome, 20).until(
                            EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[3]' ) )) 
                            aposta_fora.click()

                            self.insere_valor( f'{self.valor_aposta:.2f}')

                    elif odd_empate >= 3.00 and odd_fora >= 3.00 and odd_casa >= 2:                                        
                        
                            aposta_casa = WebDriverWait(self.chrome, 20).until(
                            EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[1]' ) )) 
                            aposta_casa.click()
                            
                            self.insere_valor( f'{self.valor_aposta:.2f}')                        

                    else:
                        print('JOGO SEM APOSTA')
                        self.aposta_fechada = True
                elif self.estilo_rodada == EstiloJogo.ZEBRA_COM_ODD_MAIOR_IGUAL_2:
                    if odd_casa >= odd_fora and odd_empate >= 3.00 and odd_fora >= 2.00:

                        aposta_casa = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[1]' ) )) 
                        aposta_casa.click()

                        aposta_empate = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[2]' ) )) 
                        aposta_empate.click()   

                        self.insere_valor( f'{self.valor_aposta:.2f}')

                    elif odd_empate >= 3.00 and odd_fora >= odd_casa and odd_casa >= 2.00:                
                        
                        aposta_empate = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[2]' ) )) 
                        aposta_empate.click()

                        aposta_fora = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[3]' ) )) 
                        aposta_fora.click()            

                        self.insere_valor( f'{self.valor_aposta:.2f}')
                        
                    else:
                        print('JOGO SEM APOSTA')
                        self.aposta_fechada = True
                elif self.estilo_rodada == EstiloJogo.FAVORITO_COM_ODD_MENOR_1_E_MEIO:
                    if odd_casa >= 3.00 and odd_empate >= 3.00 and odd_fora < 1.8:

                        aposta_fora = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[3]' ) )) 
                        aposta_fora.click()

                        self.insere_valor( f'{self.valor_aposta:.2f}')
                    elif odd_empate >= 3.00 and odd_fora >= 3.00 and odd_casa < 1.8:                                        
                        
                        aposta_casa = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[1]' ) )) 
                        aposta_casa.click()
                        
                        self.insere_valor( f'{self.valor_aposta:.2f}')                                              
                    else:
                        print('JOGO SEM APOSTA')
                        self.aposta_fechada = True
                elif self.estilo_rodada == EstiloJogo.FAVORITO_EMPATE_COM_ODD_MAIOR_IGUAL_2:
                    if odd_casa >= 2.00 and odd_empate >= 3.00 and odd_casa <= odd_fora:
                         
                        aposta_casa = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[1]' ) )) 
                        aposta_casa.click()

                        aposta_empate = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[2]' ) )) 
                        aposta_empate.click()         

                        self.insere_valor( f'{self.valor_aposta:.2f}')
                    elif odd_fora >= 2.00 and odd_empate >= 3.00 and odd_fora <= odd_casa:
                        aposta_empate = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[2]' ) )) 
                        aposta_empate.click()

                        aposta_fora = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[1]/ms-regular-group/ms-regular-option-group/div/ms-option[3]' ) )) 
                        aposta_fora.click()                 

                        self.insere_valor( f'{self.valor_aposta:.2f}')
                    else:
                        print('JOGO SEM APOSTA')
                        self.aposta_fechada = True
                elif self.estilo_rodada == EstiloJogo.TOTAL_GOLS:
                    odd_abaixo_1_5 = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[2]/ms-option-panel[1]/ms-over-under-option-group/div/ms-option[4]' ) )) 
                    odd_abaixo_1_5.click()

                    odd_acima_2_5 = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[2]/ms-option-panel[1]/ms-over-under-option-group/div/ms-option[5]' ) )) 
                    odd_acima_2_5.click()

                    self.insere_valor( f'{self.valor_aposta:.2f}')
                elif self.estilo_rodada == EstiloJogo.DOIS_GOLS_OU_ABAIXO_1_E_MEIO:
                    odd_abaixo_1_5 = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[2]/ms-option-panel[1]/ms-over-under-option-group/div/ms-option[4]' ) )) 
                    odd_abaixo_1_5.click()

                    dois_gols = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[1]/ms-option-panel[2]/ms-regular-group/ms-regular-option-group/div/ms-option[3]' ) )) 
                    dois_gols.click()

                    self.insere_valor( f'{self.valor_aposta:.2f}')
                elif self.estilo_rodada == EstiloJogo.JOGO_UNICO_ODD_ABAIXO_2_MEIO:           
                    odd_mais_1_meio = WebDriverWait(self.chrome, 20).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[2]/ms-option-panel[1]/ms-over-under-option-group/div/ms-option[3]/ms-event-pick/div/div[2]') ))  
                    odd_mais_1_meio = float(odd_mais_1_meio.get_property('innerText'))

                    # vamos pegar quanto é meio por cento do valor do saldo
                    # se tiver perda acumulada, vai apostar o valor pra recuperar a perda
                    if self.tipo_valor == TipoValorAposta.PORCENTAGEM:
                        self.valor_aposta = ( self.saldo * self.valor_aposta_inicial / 100 + self.perda_acumulada ) / (odd_mais_2_meio - 1.0)
                    elif self.tipo_valor == TipoValorAposta.VALOR_ABSOLUTO:
                        self.valor_aposta = ( self.valor_aposta_inicial + self.perda_acumulada ) / (odd_mais_2_meio - 1.0)

                    self.saldo_antes_aposta = self.saldo

                    print(f'PERDA ACUMULADA: {self.perda_acumulada:.2f} R$')
                    print(f'VALOR DA APOSTA: {self.valor_aposta:.2f} R$')                    
                    print(f'GANHO POTENCIAL: {(self.valor_aposta * odd_mais_1_meio):.2f} R$')
                    print(f'GANHO POTENCIAL REAL: {(self.valor_aposta * odd_mais_1_meio - self.valor_aposta):.2f} R$')

                    odd_acima_1_5 = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[2]/ms-option-panel[1]/ms-over-under-option-group/div/ms-option[3]' ) )) 
                    odd_acima_1_5.click()

                    self.insere_valor( f'{self.valor_aposta:.2f}')
                elif self.estilo_rodada == EstiloJogo.JOGO_UNICO_ODD_ACIMA_2_MEIO:
                    odd_mais_2_meio = WebDriverWait(self.chrome, 20).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[2]/ms-option-panel[1]/ms-over-under-option-group/div/ms-option[5]/ms-event-pick/div/div[2]') ))  
                    odd_mais_2_meio = float(odd_mais_2_meio.get_property('innerText'))

                    # vamos pegar quanto é meio por cento do valor do saldo
                    # se tiver perda acumulada, vai apostar o valor pra recuperar a perda
                    if self.tipo_valor == TipoValorAposta.PORCENTAGEM:
                        self.valor_aposta = ( self.saldo_inicial * self.valor_aposta_inicial / 100 + self.perda_acumulada ) / (odd_mais_2_meio - 1.0)
                    elif self.tipo_valor == TipoValorAposta.VALOR_ABSOLUTO:
                        self.valor_aposta = ( self.valor_aposta_inicial + self.perda_acumulada ) / (odd_mais_2_meio - 1.0)

                    # pra não quebrar o algoritmo, se o valor da aposta for menor do que 2 a gente ajusta pra 2
                    if self.valor_aposta < 2.00:
                        self.valor_aposta = 2.00

                    # se valor da aposta for menor do que o saldo o programa vai fechar e enviar mensagem
                    if self.valor_aposta > self.saldo:
                        self.chrome.quit()
                        print('SALDO INSUFICIENTE PARA REALIZAR APOSTAS!!!')
                        self.telegram_bot.envia_mensagem(f'SALDO INSUFICIENTE PARA REALIZAR APOSTAS!!!')
                        exit()

                    self.saldo_antes_aposta = self.saldo

                    print(f'PERDA ACUMULADA: {self.perda_acumulada:.2f} R$')
                    print(f'VALOR DA APOSTA: {self.valor_aposta:.2f} R$')                    
                    print(f'GANHO POTENCIAL: {(self.valor_aposta * odd_mais_2_meio):.2f} R$')
                    print(f'GANHO POTENCIAL REAL: {(self.valor_aposta * odd_mais_2_meio - self.valor_aposta):.2f} R$')

                    odd_acima_2_meio = WebDriverWait(self.chrome, 20).until(
                        EC.element_to_be_clickable((By.XPATH, '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-option-group-list/div[2]/ms-option-panel[1]/ms-over-under-option-group/div/ms-option[5]' ) )) 
                    odd_acima_2_meio.click()

                    self.insere_valor( f'{self.valor_aposta:.2f}')

        except Exception as e:
            print("APOSTA JÁ FECHADA...")
            print('Algo saiu errado no analisa_odds')
            print(e)
            self.aposta_fechada = True

    def le_saldo(self):
        try:
            saldo_request = self.chrome.execute_script(f'let d = await fetch("https://sports.sportingbet.com/pt-br/api/balance/refresh"); return await d.json();')
            self.saldo = saldo_request['vnBalance']['accountBalance']
        except Exception as e:
            print(e)
            print('Não foi possível ler saldo. Saindo do programa.')
            self.chrome.quit()
            exit()

    def define_hora_jogo(self, hora_jogo_atual):
        hora = int(hora_jogo_atual.split(':')[0])
        minuto = int(hora_jogo_atual.split(':')[1])
        now = datetime.today()  
        hora_do_jogo = datetime( now.year, now.month, now.day, hora, minuto, 0)
        hora_jogo_atual_datetime = hora_do_jogo + timedelta(minutes=3)
        hora_jogo_atual =  hora_jogo_atual_datetime.strftime("%H:%M")
        self.hora_jogo = hora_jogo_atual
        return hora_jogo_atual

    def gera_array_randomico(self):
        array_randomico = []
        for _ in range(1000):
            array_randomico.append( randrange(2) )
        print(array_randomico)
        return array_randomico
    
    def espera_resultado_jogo(self, horario_jogo):
        if not self.aposta_fechada:
            print('Entrou no espera_resultado_jogo')
            try:
                print('HORÁRIO', self.hora_jogo )
                print('Esperando resultado da partida...')
                hora = int(self.hora_jogo.split(':')[0])
                minuto = int(self.hora_jogo.split(':')[1])
                now = datetime.today()  
                hora_do_jogo = datetime( now.year, now.month, now.day, hora, minuto, 0)

                self.le_saldo()
                self.saldo_antes_aposta = self.saldo

                pause.until( hora_do_jogo + timedelta(minutes=1, seconds=20)  )

                numero_apostas_abertas = self.chrome.execute_script(f'let d = await fetch("https://sports.sportingbet.com/pt-br/sports/api/mybets/betslips?index=1&maxItems=12&typeFilter=2"); return await d.json();')
                numero_apostas_abertas = numero_apostas_abertas['summary']['openBetsCount']

                contador_de_trava = 0

                # enquanto a aposta não for liquidada o script vai ficar buscando aqui
                while numero_apostas_abertas == 1:
                    numero_apostas_abertas = self.chrome.execute_script(f'let d = await fetch("https://sports.sportingbet.com/pt-br/sports/api/mybets/betslips?index=1&maxItems=12&typeFilter=2"); return await d.json();')
                    numero_apostas_abertas = numero_apostas_abertas['summary']['openBetsCount']
                    contador_de_trava += 1
                    if contador_de_trava == 10:
                        self.telegram_bot.envia_mensagem(f'SISTEMA POSSIVELMENTE TRAVADO!!!')
                    sleep(5)

                # agora verifico se o horário da partida é igual a self.hora_jogo
                horario_ultima_aposta = self.chrome.execute_script(f'let d = await fetch("https://sports.sportingbet.com/pt-br/sports/api/mybets/betslips?index=1&maxItems=1&typeFilter=2"); return await d.json();')
                horario_ultima_aposta_texto = horario_ultima_aposta['betslips'][0]['bets'][0]['fixture']['date']
                horario_ultima_aposta_texto = horario_ultima_aposta_texto.replace('Z', '')
                horario_ultima_aposta_texto = datetime.strptime( horario_ultima_aposta_texto, '%Y-%m-%dT%H:%M:%S') 
                horario_ultima_aposta_texto = ( horario_ultima_aposta_texto - timedelta(hours=3) ).strftime("%H:%M")

                contador_de_trava = 0

                # enquanto for diferente é porque a última aposta não saiu
                while horario_ultima_aposta_texto != self.hora_jogo:
                    horario_ultima_aposta = self.chrome.execute_script(f'let d = await fetch("https://sports.sportingbet.com/pt-br/sports/api/mybets/betslips?index=1&maxItems=1&typeFilter=2"); return await d.json();')
                    horario_ultima_aposta_texto = horario_ultima_aposta['betslips'][0]['bets'][0]['fixture']['date']
                    horario_ultima_aposta_texto = horario_ultima_aposta_texto.replace('Z', '')
                    horario_ultima_aposta_texto = datetime.strptime( horario_ultima_aposta_texto, '%Y-%m-%dT%H:%M:%S') 
                    horario_ultima_aposta_texto = ( horario_ultima_aposta_texto - timedelta(hours=3) ).strftime("%H:%M")
                    contador_de_trava += 1
                    if contador_de_trava == 10:
                        self.telegram_bot.envia_mensagem(f'SISTEMA POSSIVELMENTE TRAVADO!!!')
                    sleep(5)
                
                print('JÁ SAIU RESULTADO')
                # agora vamos conferir se foi favorável ou não              

                contador_de_trava = 0

                self.le_saldo()

                if horario_ultima_aposta['betslips'][0]['bets'][0]['state'] == 'Won':
                    # se tiver ganhado, vai buscar o saldo até que o mesmo esteja atualizado
                    while self.saldo <= self.saldo_antes_aposta:
                        print('SALDO ATUALIZADO?', self.saldo > self.saldo_antes_aposta)
                        self.le_saldo()
                        sleep(5)

                        contador_de_trava += 1
                        if contador_de_trava == 10:
                            self.telegram_bot.envia_mensagem(f'SISTEMA POSSIVELMENTE TRAVADO!!!')
                    print('GANHOU.')
                    self.perdidas_em_sequencia = 0
                else:
                    self.perdidas_em_sequencia += 1
                    if self.maior_perdidas_em_sequencia < self.perdidas_em_sequencia:
                        self.maior_perdidas_em_sequencia = self.perdidas_em_sequencia
                    print('PERDEU.')

                print(f'SALDO ATUAL: {self.saldo}')

                # depois de ler saldo a gente analisa se ganhamos ou perdemos
                if self.estilo_jogo == EstiloJogo.JOGO_UNICO_ODD_ABAIXO_2_MEIO or self.estilo_jogo == EstiloJogo.JOGO_UNICO_ODD_ACIMA_2_MEIO:
                    # significa que perdemos, então vamos adicionar a perda ao valor acumulado
                    if self.saldo <= self.saldo_antes_aposta:
                        self.perda_acumulada += self.valor_aposta
                        self.contador_perdas += 1
                    # significa que recuperamos o valor perdido, então zeramos a perda acumulada
                    elif self.saldo > self.saldo_antes_aposta:
                        self.perda_acumulada = 0.0
                        self.contador_perdas = 0
                        self.telegram_bot.envia_mensagem(f'GANHO REAL! SALDO: R$ {self.saldo}')                        

                if self.contador_perdas >= 10:
                    self.telegram_bot.envia_mensagem(f'MAIS DE DEZ PERDAS ACUMULADAS!!!')

                if self.saldo >= self.meta - 0.5:
                    print('PARABÉNS! VOCÊ ATINGIU SUA META!')
                    self.telegram_bot.envia_mensagem(f'PARABÉNS! VOCÊ ATINGIU SUA META! SEU SALDO É: R$ {self.saldo}\nMAIOR SEQUÊNCIA DE PERDAS: {self.maior_perdidas_em_sequencia}')
                    print(f'MAIOR SEQUÊNCIA DE PERDAS: {self.maior_perdidas_em_sequencia}')
                    self.chrome.quit()
                    meta_atingida = True

            except Exception as e:
                print(e)
                print('Algo saiu errado no espera_resultado')        
        
class AnalisadorResultados():
    def __init__(self, n_amarelos=None):
        self.estilo_jogo = 10
        self.tipo_valor = 1
        self.valor_aposta = n_amarelos_e_porcentagem[n_amarelos]
        self.tipo_meta = 1        
        self.meta = n_amarelos_e_porcentagem[n_amarelos]
        self.ao_atingir_meta = 1

    def aposta(self):

        chrome = ChromeAuto(meta=self.meta, tipo_valor=self.tipo_valor, valor_aposta=self.valor_aposta, tipo_meta=self.tipo_meta, estilo_jogo=self.estilo_jogo, ao_atingir_meta=self.ao_atingir_meta)
        chrome.acessa('https://sports.sportingbet.com/pt-br/sports/virtual/futebol-virtual-101/international-100204?q=1')
        chrome.clica_sign_in()
        chrome.faz_login()

        horario_jogo = '/html/body/vn-app/vn-dynamic-layout-single-slot[4]/vn-main/main/div/ms-main/ng-scrollbar[1]/div/div/div/div/ms-main-column/div/ms-virtual-list/ms-virtual-fixture/div/ms-tab-bar/ms-scroll-adapter/div/div/ul/li[2]/a'

        primeiro_horario = chrome.chrome.find_element(By.XPATH, horario_jogo + '/descendant::*')
        hora_jogo_atual = primeiro_horario.get_property('innerText')
        chrome.hora_jogo = hora_jogo_atual

        while not meta_atingida:
            if chrome.jogos_realizados.get(hora_jogo_atual) == None:
                chrome.clica_horario_jogo(f"//*[normalize-space(text()) = '{hora_jogo_atual}']")
                if not chrome.aposta_fechada:
                    chrome.analisa_odds()
                    chrome.espera_resultado_jogo(f"//*[normalize-space(text()) = '{hora_jogo_atual}']")
                else:
                    print(f'APOSTA DO HORÁRIO {hora_jogo_atual} JÁ FECHADA...')
            else:
                print('APOSTA JÁ REALIZADA PARA ESTE JOGO...')

            hora_jogo_atual = chrome.define_hora_jogo(hora_jogo_atual)
            chrome.aposta_fechada = False

            if hora_jogo_atual == '20:56':
                hora_jogo_atual = '21:05'
                chrome.hora_jogo = '21:05'
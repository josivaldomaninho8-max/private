#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot de Sinais Bac Bo - ElephantBet
Versão: 2.0.0
Autor: Josivaldo Maninho
Descrição: Bot que monitora resultados do Bac Bo e envia sinais via Telegram
"""

import os
import sys
import time
import json
import logging
import requests
import schedule
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

@dataclass
class Config:
    """Classe de configuração centralizada"""
    # Telegram
    TELEGRAM_TOKEN: str = os.environ.get('TELEGRAM_TOKEN', "8819802652:AAGs9akn3f51BY8LRvUVpp8sxT7GAmBslm4")
    TELEGRAM_CHAT_ID: str = os.environ.get('TELEGRAM_CHAT_ID', "@Luckevan_bot")
    
    # ElephantBet
    EB_USERNAME: str = os.environ.get('EB_USERNAME', "925959236")
    EB_PASSWORD: str = os.environ.get('EB_PASSWORD', "Senhas.50")
    EB_BASE_URL: str = "https://elephantbet.co.ao"
    EB_LOGIN_URL: str = "https://elephantbet.co.ao/login"
    EB_BACBO_URL: str = "https://elephantbet.co.ao/pt/casino/game-view/420012128/bac-bo"
    
    # Selenium
    HEADLESS: bool = True
    TIMEOUT: int = 30
    PAGE_LOAD_WAIT: int = 10
    
    # Bot
    CHECK_INTERVAL_MINUTES: int = 2
    MAX_RESULTS: int = 20
    
    @classmethod
    def load_from_env(cls):
        """Carrega configurações do ambiente"""
        return cls()

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura o sistema de logging profissional"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_datefmt = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=log_datefmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )
    
    # Reduzir logs de bibliotecas externas
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# TELEGRAM MANAGER
# ============================================================================

class TelegramManager:
    """Gerenciador de envio de mensagens para o Telegram"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """Envia mensagem para o Telegram de forma síncrona"""
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            if response.status_code == 200:
                self.logger.info("Mensagem enviada com sucesso para o Telegram")
                return True
            else:
                self.logger.error(f"Erro na API do Telegram: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro ao enviar mensagem para Telegram: {e}")
            return False
    
    def send_startup_message(self) -> bool:
        """Envia mensagem de inicialização"""
        message = f"""
🚀 *BOT DE SINAIS BAC BO - ELEPHANTBET*

✅ Bot iniciado com sucesso!
🕐 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
📊 Monitorando resultados a cada {Config.CHECK_INTERVAL_MINUTES} minutos

*Aguardando análise...*
        """
        return self.send_message(message)

# ============================================================================
# SELENIUM MANAGER
# ============================================================================

class SeleniumManager:
    """Gerenciador do Selenium WebDriver"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.logger = logging.getLogger(__name__)
    
    def start(self) -> bool:
        """Inicia o WebDriver com configurações otimizadas"""
        try:
            self.logger.info("Iniciando WebDriver...")
            
            options = Options()
            
            # Configurações headless
            if self.headless:
                options.add_argument('--headless')
            
            # Configurações essenciais para servidor
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            
            # Configurações de janela
            options.add_argument('--window-size=1920x1080')
            
            # Anti-detecção
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            
            # User Agent realista
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Desabilitar automação
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Preferências
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_settings.popups": 0,
            }
            options.add_experimental_option("prefs", prefs)
            
            # Iniciar driver
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Definir timeout
            self.driver.implicitly_wait(self.timeout)
            
            self.logger.info("WebDriver iniciado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar WebDriver: {e}")
            return False
    
    def stop(self):
        """Fecha o WebDriver"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver fechado")
        except Exception as e:
            self.logger.error(f"Erro ao fechar WebDriver: {e}")
    
    def get_driver(self):
        """Retorna o driver atual"""
        return self.driver

# ============================================================================
# ELEPHANTBET CLIENT
# ============================================================================

class ElephantBetClient:
    """Cliente para interagir com o site da ElephantBet"""
    
    def __init__(self, selenium_manager: SeleniumManager, config: Config):
        self.selenium = selenium_manager
        self.config = config
        self.driver = selenium_manager.get_driver()
        self.logger = logging.getLogger(__name__)
        self._is_logged_in = False
    
    def login(self) -> bool:
        """Realiza login no site"""
        try:
            self.logger.info("Iniciando processo de login...")
            
            # Acessar página principal
            self.driver.get(self.config.EB_BASE_URL)
            time.sleep(5)
            
            # Tentar clicar no botão de login
            login_clicked = self._click_login_button()
            
            if not login_clicked:
                # Ir diretamente para página de login
                self.logger.info("Acessando página de login diretamente...")
                self.driver.get(self.config.EB_LOGIN_URL)
                time.sleep(5)
            
            # Preencher credenciais
            if not self._fill_credentials():
                return False
            
            # Verificar login
            self._is_logged_in = self._verify_login()
            
            if self._is_logged_in:
                self.logger.info("✅ Login realizado com sucesso!")
            else:
                self.logger.warning("⚠️ Login pode ter falhado, mas continuando...")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro no login: {e}")
            self._save_screenshot("login_error.png")
            return False
    
    def _click_login_button(self) -> bool:
        """Tenta clicar no botão de login"""
        selectors = [
            "button.sign-in",
            "a[href*='login']",
            "button[class*='login']",
            "button:contains('Entrar')",
            "a:contains('Entrar')",
            ".login-button",
            "#login-btn"
        ]
        
        for selector in selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                btn.click()
                self.logger.info(f"✅ Botão de login clicado: {selector}")
                time.sleep(3)
                return True
            except:
                continue
        
        self.logger.warning("Nenhum botão de login encontrado")
        return False
    
    def _fill_credentials(self) -> bool:
        """Preenche usuário e senha"""
        try:
            # Aguardar campos
            wait = WebDriverWait(self.driver, 20)
            
            # Campo username
            username_field = wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.clear()
            username_field.send_keys(self.config.EB_USERNAME)
            self.logger.info("✅ Username preenchido")
            
            # Campo password
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(self.config.EB_PASSWORD)
            self.logger.info("✅ Password preenchido")
            
            # Submeter
            try:
                submit = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit.click()
            except:
                password_field.send_keys(Keys.ENTER)
            
            time.sleep(5)
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao preencher credenciais: {e}")
            return False
    
    def _verify_login(self) -> bool:
        """Verifica se o login foi bem-sucedido"""
        try:
            # Verificar se URL mudou
            if "login" not in self.driver.current_url.lower():
                return True
            
            # Verificar elemento de usuário logado
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".user-menu, .profile, .user-avatar")
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar login: {e}")
            return False
    
    def get_bacbo_results(self) -> List[str]:
        """Obtém os resultados do Bac Bo"""
        try:
            self.logger.info("Coletando resultados do Bac Bo...")
            
            # Acessar página do jogo
            self.driver.get(self.config.EB_BACBO_URL)
            time.sleep(8)
            
            # Scroll para carregar elementos
            self._scroll_page()
            time.sleep(3)
            
            # Coletar resultados
            results = self._extract_results()
            
            # Tentar extrair via regex se não encontrou
            if not results:
                results = self._extract_results_from_html()
            
            self.logger.info(f"📊 {len(results)} resultados coletados")
            return results
            
        except Exception as e:
            self.logger.error(f"Erro ao coletar resultados: {e}")
            return []
    
    def _scroll_page(self):
        """Rola a página para carregar conteúdo dinâmico"""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(2)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)
    
    def _extract_results(self) -> List[str]:
        """Extrai resultados usando seletores CSS"""
        results = []
        selectors = [
            ".history-result-circle",
            ".result-circle",
            ".history-item .result",
            "[class*='history'] [class*='circle']",
            ".game-result",
            ".result-history .item",
            "[class*='result'] [class*='history'] span"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for el in elements[:self.config.MAX_RESULTS]:
                        text = el.text.strip().upper()
                        result = self._normalize_result(text)
                        if result:
                            results.append(result)
                    
                    if results:
                        self.logger.debug(f"✅ Resultados com seletor: {selector}")
                        break
            except:
                continue
        
        return results
    
    def _extract_results_from_html(self) -> List[str]:
        """Fallback: extrai resultados do HTML usando regex"""
        import re
        
        self.logger.info("Tentando extrair resultados do HTML...")
        html = self.driver.page_source
        
        patterns = [
            r'[BPT](?=\s|$|<|")',
            r'BANCO|JOGADOR|EMPATE',
            r'class="[^"]*result[^"]*"[^>]*>([BPT])',
            r'>([BPT])</'
        ]
        
        results = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches[:self.config.MAX_RESULTS]:
                result = self._normalize_result(match)
                if result:
                    results.append(result)
            if results:
                break
        
        return results
    
    def _normalize_result(self, text: str) -> Optional[str]:
        """Normaliza o texto do resultado"""
        text = text.upper().strip()
        
        if text in ["B", "BANCO", "BANK"]:
            return "B"
        elif text in ["P", "JOGADOR", "PLAYER"]:
            return "P"
        elif text in ["T", "EMPATE", "TIE"]:
            return "T"
        else:
            return None
    
    def _save_screenshot(self, filename: str):
        """Salva screenshot para debug"""
        try:
            self.driver.save_screenshot(filename)
            self.logger.info(f"📸 Screenshot salvo: {filename}")
        except:
            pass
    
    def is_logged_in(self) -> bool:
        """Retorna status do login"""
        return self._is_logged_in

# ============================================================================
# ANALISADOR DE SINAIS
# ============================================================================

class SignalAnalyzer:
    """Analisa os resultados e gera sinais de aposta"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.history = []
    
    def analyze(self, results: List[str]) -> Dict:
        """
        Analisa os resultados e retorna um sinal
        
        Returns:
            Dict com análise detalhada
        """
        if not results or len(results) < 3:
            return {
                'signal': 'Aguardando dados...',
                'confidence': 0,
                'details': {
                    'B': 0,
                    'P': 0,
                    'T': 0,
                    'total': 0,
                    'analysis': 'Dados insuficientes para análise'
                },
                'recommendation': '📊 Aguarde mais resultados'
            }
        
        # Atualizar histórico
        self.history.extend(results)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        
        # Últimos 10 resultados
        recent = results[:10]
        
        # Contar ocorrências
        counts = {'B': 0, 'P': 0, 'T': 0}
        for r in recent:
            if r in counts:
                counts[r] += 1
        
        total = len(recent)
        percentages = {
            k: (v / total * 100) if total > 0 else 0
            for k, v in counts.items()
        }
        
        # Determinar sinal
        signal = self._determine_signal(counts, percentages)
        
        # Gerar análise
        analysis = self._generate_analysis(counts, percentages, recent)
        
        return {
            'signal': signal,
            'confidence': max(percentages.values()),
            'details': {
                'B': counts['B'],
                'P': counts['P'],
                'T': counts['T'],
                'total': total,
                'analysis': analysis,
                'percentages': percentages
            },
            'recommendation': self._get_recommendation(signal),
            'recent_results': recent
        }
    
    def _determine_signal(self, counts: Dict, percentages: Dict) -> str:
        """Determina o sinal baseado nas contagens"""
        # Prioridade: B > P > T
        if percentages['B'] >= 40:
            return 'BANCO'
        elif percentages['P'] >= 40:
            return 'JOGADOR'
        elif percentages['T'] >= 35:
            return 'EMPATE'
        else:
            # Escolher o mais frequente
            return max(counts, key=counts.get).replace('B', 'BANCO').replace('P', 'JOGADOR').replace('T', 'EMPATE')
    
    def _generate_analysis(self, counts: Dict, percentages: Dict, recent: List[str]) -> str:
        """Gera análise detalhada"""
        analysis = []
        
        # Análise de tendência
        if percentages['B'] >= 40:
            analysis.append(f"🔵 Banco com {percentages['B']:.1f}% das ocorrências")
        elif percentages['P'] >= 40:
            analysis.append(f"🔴 Jogador com {percentages['P']:.1f}% das ocorrências")
        elif percentages['T'] >= 30:
            analysis.append(f"🟡 Empate com {percentages['T']:.1f}% das ocorrências")
        else:
            analysis.append("📊 Distribuição equilibrada")
        
        # Análise de sequência
        if len(recent) >= 3:
            last_3 = recent[:3]
            if len(set(last_3)) == 1:
                analysis.append(f"🔥 Sequência de {last_3[0]} nos últimos 3")
        
        return " | ".join(analysis)
    
    def _get_recommendation(self, signal: str) -> str:
        """Gera recomendação baseada no sinal"""
        emojis = {
            'BANCO': '🔵',
            'JOGADOR': '🔴',
            'EMPATE': '🟡'
        }
        return f"{emojis.get(signal, '📊')} Sugestão: APOSTAR EM {signal}"
    
    def format_message(self, analysis: Dict) -> str:
        """Formata a mensagem para o Telegram"""
        details = analysis['details']
        recent = ' '.join(analysis['recent_results'][:10])
        
        message = f"""
🎯 *SINAL BAC BO - ELEPHANTBET*

📊 *Análise:* {analysis['signal']}
📈 *Confiança:* {analysis['confidence']:.1f}%

📋 *Últimos 10 resultados:*
{recent}

📊 *Estatísticas:*
🔵 Banco: {details['B']} | 🔴 Jogador: {details['P']} | 🟡 Empate: {details['T']}

💡 *Recomendação:*
{analysis['recommendation']}

📝 *Análise detalhada:*
{details['analysis']}

⏰ *Atualizado:* {datetime.now().strftime('%H:%M:%S')}
        """
        return message

# ============================================================================
# BOT PRINCIPAL
# ============================================================================

class BacBoBot:
    """Bot principal que orquestra todas as funcionalidades"""
    
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.telegram = TelegramManager(self.config.TELEGRAM_TOKEN, self.config.TELEGRAM_CHAT_ID)
        self.selenium = SeleniumManager(headless=self.config.HEADLESS, timeout=self.config.TIMEOUT)
        self.client = None
        self.analyzer = SignalAnalyzer()
        self.running = False
    
    def start(self):
        """Inicia o bot"""
        self.logger.info("=" * 60)
        self.logger.info("🚀 INICIANDO BOT DE SINAIS BAC BO")
        self.logger.info("=" * 60)
        
        try:
            # Enviar mensagem de inicialização
            self.telegram.send_startup_message()
            
            # Iniciar Selenium
            if not self.selenium.start():
                self.logger.error("❌ Falha ao iniciar Selenium")
                self.telegram.send_message("❌ *ERRO:* Falha ao iniciar navegador")
                return
            
            # Inicializar cliente
            self.client = ElephantBetClient(self.selenium, self.config)
            
            # Realizar login
            if not self.client.login():
                self.logger.warning("⚠️ Login pode ter falhado, continuando...")
                self.telegram.send_message("⚠️ *ALERTA:* Login pode ter falhado. Verificando...")
            
            # Agendar execuções
            self.running = True
            self._schedule_tasks()
            
            # Executar primeira análise
            self._analyze_and_send()
            
            # Loop principal
            self._main_loop()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Bot interrompido pelo usuário")
        except Exception as e:
            self.logger.error(f"❌ Erro fatal: {e}")
            self.telegram.send_message(f"❌ *ERRO FATAL:* {str(e)[:200]}")
        finally:
            self.shutdown()
    
    def _schedule_tasks(self):
        """Agenda as tarefas periódicas"""
        schedule.every(self.config.CHECK_INTERVAL_MINUTES).minutes.do(self._analyze_and_send)
        self.logger.info(f"⏰ Análises agendadas a cada {self.config.CHECK_INTERVAL_MINUTES} minutos")
    
    def _main_loop(self):
        """Loop principal do bot"""
        self.logger.info("🔄 Bot em execução...")
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(5)
            except Exception as e:
                self.logger.error(f"Erro no loop principal: {e}")
                time.sleep(30)
    
    def _analyze_and_send(self):
        """Executa análise e envia resultado"""
        try:
            self.logger.info("🔍 Iniciando análise...")
            
            # Obter resultados
            results = self.client.get_bacbo_results() if self.client else []
            
            if not results:
                self.logger.warning("Nenhum resultado obtido")
                self.telegram.send_message("⚠️ *AVISO:* Nenhum resultado foi obtido. Verificando conexão...")
                return
            
            # Analisar
            analysis = self.analyzer.analyze(results)
            
            # Formatar e enviar
            message = self.analyzer.format_message(analysis)
            self.telegram.send_message(message)
            
            self.logger.info(f"✅ Sinal enviado: {analysis['signal']}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro na análise: {e}")
            self.telegram.send_message(f"❌ *ERRO NA ANÁLISE:* {str(e)[:200]}")
    
    def shutdown(self):
        """Finaliza o bot de forma limpa"""
        self.logger.info("🛑 Finalizando bot...")
        self.running = False
        
        if self.selenium:
            self.selenium.stop()
        
        self.telegram.send_message("🛑 *Bot desligado*")
        self.logger.info("✅ Bot finalizado com sucesso")

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Ponto de entrada principal"""
    try:
        bot = BacBoBot()
        bot.start()
    except Exception as e:
        logger.error(f"❌ Erro fatal no main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

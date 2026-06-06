"""
Serviço de integração com IBGE para dados de população em tempo real
Documentação: https://servicodados.ibge.gov.br/
"""

import requests
from functools import lru_cache
from datetime import datetime, timedelta
import json

# Cache de 1 hora para economizar requisições
IBGE_CACHE = {}
IBGE_CACHE_EXPIRY = {}

class IBGEService:
    """Serviço para buscar dados do IBGE em tempo real"""

    BASE_URL = "https://servicodados.ibge.gov.br/api/v1"

    @staticmethod
    def get_city_info(ibge_code: int) -> dict:
        """
        Busca informações de uma cidade pelo código IBGE

        Args:
            ibge_code: Código IBGE da cidade (ex: 3550308 para São Paulo)

        Returns:
            dict com informações da cidade
        """
        # Verificar cache
        if ibge_code in IBGE_CACHE:
            if datetime.utcnow() < IBGE_CACHE_EXPIRY.get(ibge_code, datetime.utcnow()):
                return IBGE_CACHE[ibge_code]

        try:
            # API do IBGE para informações de município
            url = f"{IBGEService.BASE_URL}/municipios/{ibge_code}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                result = {
                    "id": ibge_code,
                    "name": data.get("nome"),
                    "state": data.get("microrregiao", {}).get("mesorregiao", {}).get("estado", {}).get("sigla"),
                    "success": True,
                    "cached": False,
                    "fetched_at": datetime.utcnow().isoformat()
                }

                # Salvar em cache por 1 hora
                IBGE_CACHE[ibge_code] = result
                IBGE_CACHE_EXPIRY[ibge_code] = datetime.utcnow() + timedelta(hours=1)

                return result
            else:
                return {
                    "id": ibge_code,
                    "success": False,
                    "error": f"IBGE API retornou {response.status_code}"
                }

        except requests.exceptions.Timeout:
            return {
                "id": ibge_code,
                "success": False,
                "error": "Timeout na requisição IBGE"
            }
        except Exception as e:
            return {
                "id": ibge_code,
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_state_cities(state_code: str) -> list:
        """
        Busca todas as cidades de um estado

        Args:
            state_code: Código do estado (ex: "SP", "RJ")

        Returns:
            list de cidades do estado
        """
        try:
            # Mapeamento de sigla para código IBGE do estado
            state_codes = {
                "AC": 12, "AL": 27, "AP": 16, "AM": 13, "BA": 29,
                "CE": 23, "DF": 53, "ES": 32, "GO": 52, "MA": 21,
                "MT": 51, "MS": 50, "MG": 31, "PA": 15, "PB": 25,
                "PR": 41, "PE": 26, "PI": 22, "RJ": 33, "RN": 24,
                "RS": 43, "RO": 11, "RR": 14, "SC": 42, "SP": 35,
                "SE": 28, "TO": 28
            }

            state_ibge_code = state_codes.get(state_code)
            if not state_ibge_code:
                return []

            url = f"{IBGEService.BASE_URL}/municipios?where=siglaUF:eq:{state_code}&orderBy=nome"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            print(f"Erro ao buscar cidades de {state_code}: {e}")
            return []

    @staticmethod
    def get_population_estimate(ibge_code: int, year: int = 2023) -> dict:
        """
        Busca estimativa de população para um município

        Args:
            ibge_code: Código IBGE do município
            year: Ano da estimativa (default: 2023)

        Returns:
            dict com população e dados
        """
        try:
            # API de estimativas populacionais
            url = f"{IBGEService.BASE_URL}/populacao/{ibge_code}?formato=json"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                return {
                    "ibge_code": ibge_code,
                    "population": data.get("valor"),
                    "year": year,
                    "success": True,
                    "source": "IBGE"
                }
            return {
                "ibge_code": ibge_code,
                "success": False,
                "error": f"IBGE retornou {response.status_code}"
            }

        except Exception as e:
            return {
                "ibge_code": ibge_code,
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_gdp_data(ibge_code: int) -> dict:
        """
        Busca dados de PIB municipal

        Args:
            ibge_code: Código IBGE do município

        Returns:
            dict com dados de PIB
        """
        try:
            # Esta é uma API mais complexa, implementação simplificada
            return {
                "ibge_code": ibge_code,
                "note": "PIB data disponível via API específica do IBGE",
                "url": "https://www.ibge.gov.br/explica/pib.php"
            }
        except Exception as e:
            return {
                "ibge_code": ibge_code,
                "error": str(e)
            }


# Função helper para obter dados combinados
def get_city_data_with_ibge(city_name: str, ibge_code: int, current_population: int) -> dict:
    """
    Combina dados locais com dados do IBGE

    Args:
        city_name: Nome da cidade
        ibge_code: Código IBGE
        current_population: População atual armazenada

    Returns:
        dict com dados combinados
    """
    ibge_info = IBGEService.get_city_info(ibge_code)

    result = {
        "city": city_name,
        "ibge_code": ibge_code,
        "population": {
            "stored": current_population,
            "ibge_verified": ibge_info.get("success", False),
            "last_updated": datetime.utcnow().isoformat()
        },
        "ibge_data": ibge_info
    }

    return result


if __name__ == "__main__":
    # Teste simples
    print("Testando IBGE Service...")

    # Teste São Paulo
    sp_data = IBGEService.get_city_info(3550308)
    print(f"São Paulo: {sp_data}")

    # Teste Rio de Janeiro
    rj_data = IBGEService.get_city_info(3304557)
    print(f"Rio de Janeiro: {rj_data}")

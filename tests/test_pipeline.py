import json
import os
import pytest
import httpx

# API URL via variável de ambiente (útil no docker-compose)
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")
ANALYZE_ENDPOINT = f"{API_BASE_URL}/api/feature/analyze"
ANALYZE_TEXT_ENDPOINT = f"{API_BASE_URL}/api/feature/analyze/text"

# Diretórios de onde vamos ler o padrão ouro
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUTS_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Casos de teste de 1 a 5
TEST_CASES = [1, 2, 3, 4, 5]

@pytest.fixture(scope="session")
def api_client():
    # Usando Timeout longo pois a API de IA pode demorar
    with httpx.Client(timeout=120.0) as client:
        yield client

def check_health(api_client):
    """Garante que a API está no ar antes de começar as análises"""
    try:
        resp = api_client.get(f"{API_BASE_URL}/health")
        return resp.status_code == 200
    except httpx.RequestError:
        return False

@pytest.mark.parametrize("test_id", TEST_CASES)
def test_gold_standard_pipeline(api_client, test_id):
    assert check_health(api_client), f"API {API_BASE_URL} inacessível."

    input_file = os.path.join(INPUTS_DIR, f"test_{test_id}.json")
    expected_file = os.path.join(OUTPUTS_DIR, f"test_{test_id}_expected.json")

    assert os.path.exists(input_file), f"Input test_{test_id}.json não encontrado"
    assert os.path.exists(expected_file), f"Output esperado test_{test_id}_expected.json não encontrado"

    with open(input_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    with open(expected_file, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # Verifica o tipo de endpoint baseado no payload
    if "raw_text" in payload:
        response = api_client.post(ANALYZE_TEXT_ENDPOINT, json=payload)
    else:
        response = api_client.post(ANALYZE_ENDPOINT, json=payload)

    assert response.status_code == 200, f"Erro na API: {response.text}"
    data = response.json()

    # 1. Valida estrutura (todas as chaves esperadas devem estar no JSON de resposta)
    for key in expected["expected_keys"]:
        assert key in data, f"Chave ausente na resposta: {key}"

    # 2. Valida criticidade
    assert data["criticality"] == expected["expected_criticality"], \
        f"Criticidade divergente. Esperado: {expected['expected_criticality']}, Recebido: {data['criticality']}"

    # 3. Valida se os tipos de teste contêm as strings esperadas (verificação parcial para LLM)
    returned_test_types = " ".join(data.get("recommended_test_types", []))
    for expected_substring in expected["expected_test_type_substrings"]:
        assert expected_substring in returned_test_types, \
            f"Tipo de teste esperado não sugerido pelo LLM: {expected_substring}. Retornados: {returned_test_types}"

    # 4. Valida se preencheu a documentação (não veio vazio)
    assert len(data.get("final_documentation", "")) > 50, "Documentação final gerada está vazia ou muito curta."

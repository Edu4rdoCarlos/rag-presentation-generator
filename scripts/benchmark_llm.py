import httpx
import json
import asyncio
import time

API_URL = "http://localhost:8000/api/feature/analyze/text"

# 40 Casos de Teste cobrindo diferentes domínios e complexidades
TEST_CASES = [
    "Feature: Autenticação em 2 fatores (2FA) via SMS. O usuário recebe um código de 6 dígitos no celular que expira em 5 minutos. Após 3 tentativas erradas, o envio é bloqueado por 15 minutos.",
    "Feature: Recuperação de senha por email. O sistema envia um link único válido por 24 horas. Ao clicar, o usuário pode definir uma nova senha que atenda aos requisitos de complexidade.",
    "Feature: Cadastro de usuário com validação de CPF. O sistema consulta a Receita Federal para verificar se o CPF é válido e está regular. CPFs irregulares bloqueiam o cadastro.",
    "Feature: Exclusão lógica de conta (LGPD). O usuário solicita a exclusão. Os dados são anonimizados e a conta é inativada, mas registros financeiros são mantidos por 5 anos por questões legais.",
    "Feature: Atualização de foto de perfil. O usuário faz upload de uma imagem JPG ou PNG de no máximo 5MB. A imagem é redimensionada para 256x256 pixels e salva em um bucket S3.",
    "Feature: Adicionar produto ao carrinho. Valida se há estoque disponível. Se o usuário não estiver logado, salva o carrinho na sessão temporária.",
    "Feature: Aplicar cupom de frete grátis. Válido apenas para compras acima de R$ 100 e para a região Sudeste. Não cumulativo com outros cupons.",
    "Feature: Finalizar compra com cartão de crédito. Integração com gateway de pagamento Pagar.me. Em caso de recusa, exibe o motivo retornado pelo banco.",
    "Feature: Rastreamento de pedido. Exibe uma linha do tempo com os status (Preparando, Enviado, Em trânsito, Entregue) consumindo a API da transportadora.",
    "Feature: Avaliação de produto. O usuário pode dar de 1 a 5 estrelas e escrever um comentário opcional. Só quem comprou e recebeu o produto pode avaliar.",
    "Feature: Transferência via Pix. O usuário informa a chave (CPF, email, telefone ou aleatória). O sistema valida a chave no BACEN, exibe os dados do recebedor e pede a senha de confirmação.",
    "Feature: Geração de extrato mensal em PDF. O sistema consolida as transações do mês e gera um arquivo PDF criptografado com a senha do usuário.",
    "Feature: Solicitação de empréstimo pré-aprovado. O valor é liberado na conta instantaneamente se estiver dentro do limite pré-aprovado. Sujeito à análise de fraude.",
    "Feature: Bloqueio temporário de cartão de crédito. O usuário bloqueia o cartão via app. Compras físicas e online passam a ser negadas imediatamente.",
    "Feature: Pagamento de boleto com leitor de código de barras. O app usa a câmera para ler o código, consulta a CIP para validar os dados e agenda ou paga no dia.",
    "Feature: Agendamento de consulta médica. O paciente escolhe a especialidade, médico e horário. O sistema bloqueia o horário na agenda do médico.",
    "Feature: Cancelamento de consulta com devolução de valor. Se cancelado com até 24h de antecedência, o valor é estornado. Menos que 24h retém 50%.",
    "Feature: Prescrição de medicamento digital. O médico assina digitalmente a receita (ICP-Brasil). O paciente recebe um SMS com o link para acessar o PDF.",
    "Feature: Prontuário eletrônico do paciente. Histórico de consultas, exames e medicamentos. Acesso restrito apenas ao paciente e médicos autorizados.",
    "Feature: Alerta de exames anormais. O sistema lê o resultado do laboratório e, se houver marcadores críticos, envia um push urgente para o médico responsável.",
    "Feature: Matrícula em curso online. O aluno se inscreve, o sistema verifica se há vagas (caso seja síncrono) e libera acesso aos módulos iniciais.",
    "Feature: Emissão de certificado de conclusão. Gerado automaticamente após 100% de progresso e aprovação na prova final. Inclui QR code para autenticação.",
    "Feature: Fórum de dúvidas. Alunos podem criar tópicos, responder e dar 'like'. Professores podem marcar uma resposta como 'Solução oficial'.",
    "Feature: Realização de prova múltipla escolha com tempo limite. O cronômetro não para mesmo se fechar a aba. Respostas são salvas a cada seleção.",
    "Feature: Upload de trabalho acadêmico. Permite PDF/DOCX de até 20MB. O sistema passa o arquivo por um verificador de plágio antes de liberar para o professor.",
    "Feature: Criação de postagem com imagem. Permite texto longo, hashtags e até 10 imagens. Filtra palavras ofensivas automaticamente.",
    "Feature: Curtir postagem. Atualiza o contador em tempo real via WebSocket. Impede curtidas duplicadas do mesmo usuário.",
    "Feature: Enviar solicitação de amizade. O recebedor ganha uma notificação. Limite de 1000 solicitações pendentes por conta.",
    "Feature: Chat em tempo real via WebSocket. Mensagens com confirmação de envio (1 check) e leitura (2 checks azuis).",
    "Feature: Feed de notícias algorítmico. Exibe posts com base no engajamento (likes e comentários) e recência. Insere 1 anúncio a cada 5 posts orgânicos.",
    "Feature: Rastreamento GPS de motorista em tempo real. O app do motorista envia a latitude/longitude a cada 5 segundos para o backend.",
    "Feature: Otimização de rota de entrega. Calcula o caminho mais curto usando a API do Google Maps para até 20 paradas diárias.",
    "Feature: Confirmação de entrega com assinatura digital. O motorista coleta a assinatura na tela do app e tira uma foto do local. Sincroniza offline se não houver internet.",
    "Feature: Registro de abastecimento de veículo. O motorista anota a quilometragem, litros e valor. O sistema calcula a média de km/l e alerta se estiver baixa.",
    "Feature: Alerta de manutenção preventiva. Baseado na quilometragem do veículo, avisa o gestor de frota quando precisa trocar óleo ou pastilhas.",
    "Feature: Busca de imóveis com filtros avançados. Filtros por preço, bairro, número de quartos, vagas, etc. Ordenação por relevância ou mais recentes.",
    "Feature: Calculadora de financiamento imobiliário. Calcula as parcelas SAC ou Price com base no valor de entrada, juros e prazo.",
    "Feature: Assinatura digital de contrato de aluguel. Locador, locatário e fiadores assinam via integração com a Docusign. O contrato ganha validade legal.",
    "Feature: Agendamento de visita presencial ao imóvel. O interessado escolhe um horário. O corretor responsável recebe notificação e deve confirmar.",
    "Feature: Solicitação de reparo de imóvel alugado. O inquilino abre um chamado com fotos e descrição. A imobiliária encaminha para o proprietário aprovar o orçamento."
]

async def analyze_feature(client, text, index):
    try:
        print(f"[{index:02d}/40] Analisando feature...")
        response = await client.post(API_URL, json={"raw_text": text}, timeout=90.0)
        
        if response.status_code == 200:
            print(f"[{index:02d}/40] ✅ Sucesso!")
            return response.json()
        elif response.status_code == 429:
            print(f"[{index:02d}/40] ⚠️ Rate limit da API. Aguardando 15 segundos...")
            await asyncio.sleep(15)
            return await analyze_feature(client, text, index)
        else:
            print(f"[{index:02d}/40] ❌ Erro HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[{index:02d}/40] ❌ Erro de requisição: {e}")
        return None

async def main():
    print("=====================================================")
    print("  Iniciando bateria com 40 testes no TestDoc Agent   ")
    print("=====================================================")
    results = []
    
    # limits=httpx.Limits(max_connections=1) -> envia uma por vez para evitar Rate Limit rápido
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=1)) as client:
        for i, text in enumerate(TEST_CASES, 1):
            start_time = time.time()
            result = await analyze_feature(client, text, i)
            elapsed = time.time() - start_time
            
            if result:
                results.append({
                    "id": i,
                    "input": text,
                    "output": result,
                    "time_seconds": round(elapsed, 2)
                })
            
            # Delay entre requisições para evitar erro de Rate Limit (HTTP 429) no Gemini
            await asyncio.sleep(3)
            
    # Salvar resultados em JSON e num relatório Markdown formatado
    with open("batch_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    with open("batch_results.md", "w", encoding="utf-8") as f:
        f.write("# Resultados da Bateria de 40 Testes\n\n")
        f.write("Este relatório contém a saída completa do sistema multiagente para 40 funcionalidades distintas.\n\n")
        
        for r in results:
            out = r["output"]
            f.write(f"## Teste {r['id']}: {out.get('feature_name', 'Sem nome')}\n")
            f.write(f"> **Input:** {r['input']}\n\n")
            f.write(f"- **Criticidade:** {out.get('criticality')}\n")
            f.write(f"- **Tempo de execução:** {r['time_seconds']}s\n")
            f.write(f"- **Tipos de Teste:** {', '.join(out.get('recommended_test_types', []))}\n\n")
            
            f.write(f"### Riscos Identificados:\n")
            for risk in out.get('identified_risks', []):
                f.write(f"- {risk}\n")
                
            f.write(f"\n### Cenários Priorizados:\n")
            for sc in out.get('prioritized_scenarios', []):
                f.write(f"- {sc}\n")
                
            f.write(f"\n### Justificativa da Estratégia:\n{out.get('justification')}\n")
            f.write("\n---\n\n")
            
    print("\n=====================================================")
    print("✅ Concluído! Resultados salvos em:")
    print("   - batch_results.json (Bruto)")
    print("   - batch_results.md (Formatado para leitura)")
    print("=====================================================")

if __name__ == "__main__":
    asyncio.run(main())

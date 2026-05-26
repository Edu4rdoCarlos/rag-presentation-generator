# Funcionalidade: Upload de Documento de Identidade (KYC)

## Descrição Geral
Permite que o usuário envie uma foto do seu documento de identidade (RG ou CNH) para validação do cadastro. O sistema deve receber o arquivo, validar requisitos básicos e enviar de forma segura para um serviço externo de validação antifraude.

## Regras de Negócio
- O arquivo deve ter no tamanho máximo de 5MB.
- Apenas os formatos JPG, PNG e PDF são aceitos.
- O usuário só pode tentar o envio 3 vezes em um intervalo de 24 horas (rate limit).
- O sistema não deve aceitar envio de documento se a conta do usuário já estiver validada.
- O status do perfil do usuário deve mudar para "Em Análise" logo após o upload bem-sucedido.

## Entradas Esperadas
- Payload multipart/form-data contendo o arquivo binário.
- ID do usuário extraído do token de autenticação.
- Tipo de documento selecionado no frontend (RG ou CNH).

## Saídas Esperadas
- Sucesso (200 OK): Retorno com número de protocolo e alteração de status do usuário.
- Falha de Validação (400 Bad Request): Mensagem específica sobre tamanho excedido ou formato não suportado.
- Falha de Rate Limit (429 Too Many Requests): Bloqueio temporário.

## Dependências Técnicas e Integrações Externas
- **AWS S3:** Para armazenamento seguro e temporário do arquivo da identidade.
- **Serviço Antifraude Externo:** API de terceiros para OCR e verificação de autenticidade documental.
- **UserService:** Módulo interno responsável por alterar as permissões e o status da conta.

## Possíveis Falhas Conhecidas
- Timeout na comunicação com o serviço externo de validação de identidade.
- Falha na gravação do bucket S3 devido a perdas de conexão ou falta de permissões de IAM.
- Usuário forjar a extensão do arquivo (ex: enviar um .exe renomeado para .png), burlando a validação inicial de frontend/backend.

## Criticidade Esperada
Alta

## Arquivos e Módulos Impactados
- `src/api/routes/kyc_routes.py`
- `src/services/document_upload_service.py`
- `src/integrations/aws_s3_client.py`
- `src/integrations/antifraud_client.py`
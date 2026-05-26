# API — TestDoc Agent

Com o servidor rodando, a documentação interativa está disponível em:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## `POST /api/feature/analyze`

Recebe a feature já estruturada e retorna a documentação gerada pelo pipeline.

**Exemplo de requisição**

```bash
curl -X POST http://localhost:8000/api/feature/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "feature_name": "Checkout com cupom",
    "description": "Aplica cupons de desconto durante o processo de checkout.",
    "business_rules": [
      "Cupom pode estar ativo, expirado ou esgotado.",
      "Cupom não pode ser usado duas vezes pelo mesmo usuário.",
      "Valor final não pode ficar negativo.",
      "Pagamento só deve ser criado se o pedido for válido."
    ],
    "dependencies": ["PaymentService", "CouponService", "OrderService"]
  }'
```

---

## `POST /api/feature/analyze/text`

Recebe uma **descrição em texto livre** e passa pelo Agente 0 antes de entrar no pipeline principal.

**Exemplo de requisição**

```bash
curl -X POST http://localhost:8000/api/feature/analyze/text \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Checkout com cupom de desconto. O usuário aplica um código durante a compra. Cupons expirados ou já usados devem ser rejeitados. O valor final não pode ficar negativo. Depende do PaymentService e CouponService."
  }'
```

---

## Exemplo de resposta (ambos os endpoints)

```json
{
  "feature_name": "Checkout com cupom",
  "criticality": "Crítica",
  "identified_risks": [
    "Aceitar cupom expirado.",
    "Aceitar cupom esgotado.",
    "Permitir reuso de cupom pelo mesmo usuário.",
    "Gerar valor final negativo.",
    "Criar pagamento para pedido inválido."
  ],
  "recommended_test_types": ["unitário", "integração", "E2E", "segurança"],
  "prioritized_scenarios": [
    "Validar cálculo de desconto para cupom ativo.",
    "Rejeitar cupom expirado.",
    "Impedir reutilização do cupom.",
    "Impedir valor final negativo.",
    "Criar pagamento apenas para pedido válido."
  ],
  "justification": "...",
  "final_documentation": "...",
  "reflection_logs": ["APROVADO"],
  "reflection_iteration": 1
}
```

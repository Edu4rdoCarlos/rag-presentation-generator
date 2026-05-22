#!/bin/bash
# =============================================================================
# Script de teste — Verifica integração com Google Gemini
#
# Uso:
#   1. Suba o Docker:  docker compose -f deploy/docker-compose.yml up --build
#   2. Em outro terminal:  bash test_gemini.sh
# =============================================================================

API_URL="http://localhost:8000"

echo "========================================="
echo "  TestDoc Agent — Teste de Integração"
echo "========================================="
echo ""

# ── 1. Health check ──────────────────────────────────────────────────────────
echo "🔍 [1/3] Health check..."
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
if [ "$HEALTH" = "200" ]; then
    echo "   ✅ API rodando!"
else
    echo "   ❌ API não respondeu (HTTP $HEALTH). Verifique se o Docker está up."
    exit 1
fi
echo ""

# ── 2. Teste com JSON estruturado (POST /api/v1/feature/analyze) ─────────────
echo "🧪 [2/3] Testando endpoint /api/v1/feature/analyze (JSON estruturado)..."
echo ""

curl -s -X POST "$API_URL/api/v1/feature/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "feature_name": "Checkout com cupom",
    "description": "Permite ao usuário aplicar cupons de desconto durante o checkout. O cupom reduz o valor total do pedido antes do pagamento.",
    "business_rules": [
      "Cupom não pode ser usado duas vezes pelo mesmo usuário",
      "Desconto máximo de 50% do valor total",
      "Cupom expirado deve ser rejeitado com mensagem clara",
      "Cupons não são acumuláveis"
    ],
    "dependencies": ["PaymentService", "CouponService", "UserService"]
  }' | python3 -m json.tool 2>/dev/null || echo "   ⚠️  Resposta não é JSON válido (verifique os logs do Docker)"

echo ""
echo ""

# ── 3. Teste com texto livre (POST /api/v1/feature/analyze/text) ─────────────
echo "🧪 [3/3] Testando endpoint /api/v1/feature/analyze/text (texto livre)..."
echo ""

curl -s -X POST "$API_URL/api/v1/feature/analyze/text" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Fiz uma tela de login onde o usuário informa e-mail e senha. Se errar 5 vezes, a conta é bloqueada por 30 minutos. Tem integração com Google OAuth também."
  }' | python3 -m json.tool 2>/dev/null || echo "   ⚠️  Resposta não é JSON válido (verifique os logs do Docker)"

echo ""
echo "========================================="
echo "  Testes finalizados!"
echo "========================================="

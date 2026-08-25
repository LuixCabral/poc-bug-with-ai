# poc-bug-with-ai

> **"Com MCP" PoC** — O analista N1 descreve um bug em linguagem natural; o agente de IA abre, enriquece e escalona chamados Jira automaticamente.

```
N1 → python main.py → Agno Agent (HuggingFace / Qwen2.5-72B) → Jira MCP Server → Chamado criado ✓
```

---

## Setup

### 1. Instalar dependências

```bash
uv sync
```

### 2. Configurar credenciais

Copie o arquivo de exemplo e preencha com seus valores:

```bash
cp .env.example .env
```

| Variável | Descrição |
|---|---|
| `HF_TOKEN` | Token de acesso HuggingFace — [gere aqui](https://huggingface.co/settings/tokens) |
| `JIRA_URL` | URL da instância Atlassian, ex: `https://acme.atlassian.net` |
| `JIRA_EMAIL` | E-mail vinculado à sua conta Atlassian |
| `JIRA_API_TOKEN` | [Gere um API token](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | Chave do projeto onde os tickets serão criados (ex: `PROJ`) |

---

## Uso

### Modo interativo (chat loop)

```bash
python main.py
```

```
🤖 Bug Reporter Agent (type 'exit' or Ctrl-C to quit)

You: O botão de checkout trava no Firefox quando o usuário aplica um cupom
...
✅ Ticket criado: PROJ-42
🔗 https://acme.atlassian.net/browse/PROJ-42
```

---

## Arquitetura

```
main.py  (Agno Agent + HuggingFace / Qwen2.5-72B-Instruct)
  └── MCPTools (stdio)
        └── jira_mcp_server.py  (FastMCP)
              ├── get_project_info()   [excluída do agente — usada só para diagnóstico]
              ├── search_issues()      ← verifica duplicatas antes de criar
              ├── create_issue()       ← abre o chamado estruturado
              ├── get_issue_details()  ← consulta status e histórico
              ├── add_comment()        ← adiciona contexto ao ticket
              └── list_my_reported()   ← histórico do N1
```

### Cenários suportados pelo agente

| Cenário | Exemplo de entrada N1 | Tools usadas |
|---------|----------------------|--------------| 
| **Abrir chamado** | "O login trava no Safari" | `search_issues` → `create_issue` |
| **Verificar ticket** | "Qual o status do PROJ-42?" | `get_issue_details` |
| **Adicionar detalhes** | "Esqueci: só acontece no Chrome v124" | `add_comment` |
| **Ver histórico** | "Quais tickets abri essa semana?" | `list_my_reported` |

> **Importante**: O agente **não move cards, não atribui e não resolve** tickets.
> Essas ações pertencem ao N2. O agente é o tradutor da dor do N1.

---

## Estrutura do projeto

```
poc-bug-with-ai/
├── main.py               # Entry point do agente Agno
├── jira_mcp_server.py    # Servidor FastMCP com ferramentas Jira
├── pyproject.toml        # Projeto Python e dependências (uv)
├── .env.example          # Template de variáveis de ambiente
├── .env                  # Suas credenciais (no .gitignore)
└── README.md
```

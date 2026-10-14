# Hackathon Checklist — MLH

Aplicação CLI simples em Python 3 para uma checklist de hackathon.

Implementação inicial gerada com GitHub Copilot e revisada/testada por Codex.

Uso
---
Requer Python 3.10 ou superior. Não precisa de dependências externas.

Comandos:
- `add TEXT` : adiciona uma tarefa (TEXT não pode ser vazio). Exemplo:
  - `python3 checklist.py add "Enviar formulário"`
- `list` : lista as tarefas (mostra ID, estado e texto).
  - `python3 checklist.py list`
- `done ID` : marca a tarefa com o ID como concluída.
  - `python3 checklist.py done 2`
- `remove ID` : remove a tarefa com o ID.
  - `python3 checklist.py remove 2`

Persistência
---
Os dados são salvos em:
`~/.local/share/hackathon-checklist/tasks.json`

O arquivo usa um esquema simples:
{
  "next_id": <int>,
  "tasks": [
    {"id": <int>, "text": <string>, "done": <bool>},
    ...
  ]
}

O programa valida o esquema ao carregar. Se o JSON existente estiver malformado ou inválido, o programa recusará sobrescrevê-lo (preserva o arquivo corrompido).

Salvamento atômico: grava em arquivo temporário e usa `os.replace` para substituir.

Testes
---
Os testes usam `unittest` e executam o binário via subprocess com um `HOME` isolado (TemporaryDirectory) para evitar poluir seu ambiente.

Execute:
```sh
python3 -m unittest -v
```

Execute uma instância por vez: o salvamento é atômico, mas não há bloqueio para edições simultâneas.

# PubChem Agent Meeting Notes

Исходный конспект был разбит на несколько файлов, чтобы им было проще пользоваться как рабочей документацией, а не как одним длинным свитком.

## Оглавление

1. [Overview and MVP](docs/pubchem-agent-meeting-notes/01-overview-and-mvp.md)
2. [Tools and Agent Loop](docs/pubchem-agent-meeting-notes/02-tools-and-agent-loop.md)
3. [State, Risks, and RAG](docs/pubchem-agent-meeting-notes/03-state-risks-and-rag.md)
4. [Task List](docs/pubchem-agent-meeting-notes/04-task-list.md)
5. [Implementation Guidance](docs/pubchem-agent-meeting-notes/05-implementation-guidance.md)

## Что где лежит

- `01-overview-and-mvp.md`
  - контекст проекта
  - главный вывод встречи
  - scope MVP
  - базовая архитектурная схема
- `02-tools-and-agent-loop.md`
  - разбиение на тулы
  - как переводить текущую обертку в tool calling
  - как понимать ReAct для этого проекта
- `03-state-risks-and-rag.md`
  - хранение диалога
  - ограничения и риски
  - позиция по RAG
  - как смотреть на ChemCrow и похожие системы
- `04-task-list.md`
  - детальный список задач для реализации
- `05-implementation-guidance.md`
  - практические советы
  - рекомендуемый порядок работ
  - финальный вывод

## Быстрый вход

Если нужен самый короткий путь по смыслу:

- сначала открой [Overview and MVP](docs/pubchem-agent-meeting-notes/01-overview-and-mvp.md);
- затем [Tools and Agent Loop](docs/pubchem-agent-meeting-notes/02-tools-and-agent-loop.md);
- потом [Task List](docs/pubchem-agent-meeting-notes/04-task-list.md).

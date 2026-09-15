# Política de publicação do ALIYVO

A partir de 2026-09-15, nenhuma versão nova deve virar atualização oficial apenas por compilar ou gerar ZIP.

## Regras obrigatórias

1. Partir sempre da última versão confirmada abrindo no PC real do usuário.
2. Nunca usar uma versão que apresentou falha de inicialização como base para a próxima correção.
3. Gerar primeiro uma versão candidata/RC, não marcada como `latest`.
4. Validar o `main.py` e `updater_worker.pyw` com `py_compile`.
5. Executar teste de importação/inicialização do `main.py` em Windows para capturar erros de ordem de definição, NameError e falhas de startup antes da publicação.
6. Validar o ZIP final depois da compactação, incluindo versão interna correta.
7. Confirmar que o `updater_worker.pyw` não mudou quando a tarefa não envolve o atualizador.
8. Para mudanças envolvendo WebView2/WhatsApp, verificar separadamente que o Assistente não compartilha o mesmo WebView2 quando isso puder afetar o WhatsApp.
9. Só promover a versão para `latest` depois de todos os testes automatizáveis passarem.
10. Recursos que exigem sessão autenticada do WhatsApp (ligações, comportamento real de conversa, permissões já existentes no perfil) não podem ser declarados como confirmados apenas pelo CI. Devem ser descritos como pendentes de validação em uso real.

## Regra de comunicação

- `build passou` = compilação/empacotamento aprovados.
- `startup passou` = o módulo foi carregado/inicializado no teste sem erro imediato.
- `runtime confirmado` = o usuário testou no PC real e confirmou o comportamento.

Esses três estados nunca devem ser tratados como equivalentes.

SIMULADOR OSI — versão ajustada aos requisitos do enunciado

Executar em desenvolvimento:
  cd src
  python main.py

Gerar executável Windows:
  execute build_exe.bat
  resultado: dist\SimuladorOSI.exe

Cobertura implementada:
- 7 camadas nos hosts; roteadores restritos a L1-L3.
- Encapsulamento/desencapsulamento e PDU visual.
- Cifra XOR didática na L6, aplicada só na origem e removida só no destino.
- Sessão, portas, segmentação >=3 no C7 e remontagem.
- Dijkstra, entrega direta e indireta, falha de enlace.
- Novo quadro/MAC a cada salto; IP origem/destino constante.
- Detecção de erro e descarte sem subir camadas.
- Casos C1-C7 selecionáveis.
- V1 mapa + interfaces + caminho destacado.
- V2 pilhas por dispositivo e camada ativa.
- V3 PDU em blocos.
- V4 IP e MAC simultâneos.
- V5 passo, contínuo, pausa e 3 velocidades.
- V6 log rolável no formato pedido + salvar.
- V7 alternância OSI/TCP-IP.
- Métricas de dados úteis, transmitidos, eficiência e sobrecarga + comparação C1/C2.
- topologia em JSON externo, sem caminho absoluto.

Observação: valide a aparência e o empacotamento no Windows usado na apresentação.

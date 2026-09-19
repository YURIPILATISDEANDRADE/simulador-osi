import json
import os

from dispositivos import *
import heapq

_DIR_BASE = os.path.dirname(os.path.abspath(__file__))
Topologia = os.path.join(_DIR_BASE, "topologia.json")

#Uniformiza o formato do topologia.json. Computador vs
#Roteador e decidido pelo formato do dado (str = uma interface,
#list = varias), nao pelo nome do dispositivo - assim o arquivo
#de topologia continua podendo ser trocado livremente (requisito
#do enunciado: trocar a rede so trocando o JSON).

def _normalizar_interfaces(bruto):

    if bruto["type"] == "HOST":
        return [{
            "dispositivo": bruto["name"],
            "IPv4": bruto["ip"],
            "fisico": bruto["phys-addr"],
        }]

    interfaces = []
    for i, iface in enumerate(bruto["ports"]):
        interfaces.append({
            "dispositivo": iface["name"],
            "info": iface.get("info", ""),
            "custo": iface.get("cost"),
            "IPv4": bruto["ip"],
            "fisico": bruto["phys-addr"],
        })
    return interfaces

#Le o JSON da topologia e devolve a lista de dicts crus.
def _carregar_bruto(caminho=None):
    caminho_completo = caminho or Topologia
    try:
        with open(caminho_completo, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: '{caminho_completo}' file was not found.")
        return []

#Le o arquivo de topologia e devolve {nome: Dispositivo}.
def carregar_dispositivos(caminho="topologia.json"):
    caminho_completo = os.path.join(_DIR_BASE, caminho) if not os.path.isabs(caminho) else caminho
    data = _carregar_bruto(caminho_completo)

    dispositivos = {}
    for bruto in data:
        nome = bruto["dispositivo"]
        interfaces = _normalizar_interfaces(bruto)
        eh_computador = isinstance(bruto["interface"], str)
        classe = Computador if eh_computador else Roteador
        dispositivos[nome] = classe(nome, interfaces)
    return dispositivos

# Prefixo /24: os 3 primeiros octetos do IPv4.
def _prefixo_rede(ip):
    return ".".join(ip.split(".")[:3])

#Monta, a partir do topologia.json:
#    - grafo: {roteador: {roteador_vizinho: custo}}, so enlaces
#    roteador-roteador (interfaces cujo info comeca com 'para ').
#    - lans: {prefixo_rede: (roteador_de_entrada, nome_da_interface_local)},
#    para as interfaces de roteador que dao numa rede local (info
#    'Rede X'), usado para saber por qual roteador uma rede e servida.

def _construir_grafo():
    grafo = {}
    lans = {}
    for bruto in _carregar_bruto():
        if isinstance(bruto["interface"], str):
            continue  # e host, nao participa do grafo de roteadores
        nome_roteador = bruto["dispositivo"]
        grafo.setdefault(nome_roteador, {})
        for i, iface in enumerate(bruto["interface"]):
            info = iface.get("info", "")
            ip = bruto["IPv4"][i][""]
            if info.startswith("para "):
                vizinho = info[len("para "):].strip()
                custo = iface.get("custo")
                if custo is not None:
                    grafo[nome_roteador][vizinho] = custo
            else:
                lans[_prefixo_rede(ip)] = (nome_roteador, iface[""])
    return grafo, lans

#Interface normalizada do roteador nome_roteador cujo info e
#'para {nome_vizinho}'. None se nao existir tal interface.

def _iface_para_vizinho(nome_roteador, nome_vizinho):
    for bruto in _carregar_bruto():
        if bruto["dispositivo"] != nome_roteador or isinstance(bruto["interface"], str):
            continue
        for i, iface in enumerate(bruto["interface"]):
            if iface.get("info", "") == f"para {nome_vizinho}":
                return _normalizar_interfaces(bruto)[i]
    return None

#Caminho de menor custo a partir de origem. Devolve o dict
#'anterior', usado para reconstruir o caminho ate qualquer destino.

def _dijkstra(grafo, origem):
    dist = {origem: 0}
    anterior = {}
    fila = [(0, origem)]
    visitados = set()
    while fila:
        d, atual = heapq.heappop(fila)
        if atual in visitados:
            continue
        visitados.add(atual)
        for vizinho, custo in grafo.get(atual, {}).items():
            nova_dist = d + custo
            if nova_dist < dist.get(vizinho, float("inf")):
                dist[vizinho] = nova_dist
                anterior[vizinho] = atual
                heapq.heappush(fila, (nova_dist, vizinho))
    return anterior


def _reconstruir_caminho(anterior, origem, destino):
    if destino == origem:
        return [origem]
    if destino not in anterior:
        return None
    caminho = [destino]
    while caminho[-1] != origem:
        caminho.append(anterior[caminho[-1]])
    return list(reversed(caminho))

#IP da (unica) interface de um host. Usado pela camada 3 para
#preencher o par de enderecos logicos na origem.

def ip_de(nome):

    dispositivo = carregar_dispositivos().get(nome)
    return dispositivo.interfaces[0]["IPv4"] if dispositivo else None

#Decide o proximo salto no caminho de menor custo entre
#    dispositivo_atual e destino_nome (requisito R5).

#    Devolve (proximo_dispositivo, iface_saida, iface_entrada) ou
#    (None, None, None) se o destino for inalcancavel.
#    - proximo_dispositivo: objeto Computador/Roteador que recebe o
#      quadro no enlace atual (pode ja ser o destino final).
#    - iface_saida: interface normalizada de dispositivo_atual usada
#      para transmitir (dela sai o endereco fisico de origem, R3).
#    - iface_entrada: interface normalizada de proximo_dispositivo do
#      lado que recebe (dela sai o endereco fisico de destino, R3).

def proximo_salto(dispositivo_atual, destino_nome):

    dispositivos = carregar_dispositivos()
    destino = dispositivos.get(destino_nome)
    if destino is None or dispositivo_atual.nome == destino_nome:
        return None, None, None

    grafo, lans = _construir_grafo()
    prefixo_destino = _prefixo_rede(destino.interfaces[0]["IPv4"])
    router_destino, iface_destino_nome = lans.get(prefixo_destino, (None, None))
    if router_destino is None:
        return None, None, None

    if not isinstance(dispositivo_atual, Roteador):
        # dispositivo_atual e um host (Computador)
        prefixo_atual = _prefixo_rede(dispositivo_atual.interfaces[0]["IPv4"])
        if prefixo_atual == prefixo_destino:
            # C1: entrega direta, mesma rede local, sem roteador
            return destino, dispositivo_atual.interfaces[0], destino.interfaces[0]

        router_entrada_nome, iface_router_local = lans.get(prefixo_atual, (None, None))
        if router_entrada_nome is None:
            return None, None, None
        proximo = dispositivos[router_entrada_nome]
        iface_entrada = proximo.interface_por_nome(iface_router_local)
        return proximo, dispositivo_atual.interfaces[0], iface_entrada

    # dispositivo_atual e um Roteador
    if dispositivo_atual.nome == router_destino:
        # ultimo salto: entrega na rede local do destino
        iface_saida = dispositivo_atual.interface_por_nome(iface_destino_nome)
        return destino, iface_saida, destino.interfaces[0]

    anterior = _dijkstra(grafo, dispositivo_atual.nome)
    caminho = _reconstruir_caminho(anterior, dispositivo_atual.nome, router_destino)
    if not caminho or len(caminho) < 2:
        return None, None, None

    proximo_nome = caminho[1]
    proximo = dispositivos[proximo_nome]
    iface_saida = _iface_para_vizinho(dispositivo_atual.nome, proximo_nome)
    iface_entrada = _iface_para_vizinho(proximo_nome, dispositivo_atual.nome)
    return proximo, iface_saida, iface_entrada


# Injecao manual de erro de bit (C6). Sera acionada pela interface (V6);
# ate la, chame armar_erro_de_transmissao("R4", "R3") antes de origem.enviar(...)
# para reproduzir o cenario E6 do enunciado.
_ERRO_PENDENTE = None  # (nome_origem, nome_destino) do enlace com erro agendado, ou None


#Agenda a corrupcao de 1 bit no PROXIMO quadro que atravessar o
#enlace nome_origem -> nome_destino. Disparo unico: depois de
#corromper um quadro, o agendamento se limpa sozinho.

def armar_erro_de_transmissao(nome_origem, nome_destino):

    global _ERRO_PENDENTE
    _ERRO_PENDENTE = (nome_origem, nome_destino)

#Chamado por Lay_1.transmitir a cada quadro. Devolve True (e
#limpa o agendamento) se HAVIA um erro agendado exatamente para
#este enlace nesta direcao.
def consumir_erro_pendente(nome_origem, nome_destino):
    global _ERRO_PENDENTE
    if _ERRO_PENDENTE == (nome_origem, nome_destino):
        _ERRO_PENDENTE = None
        return True
    return False


def buscar_dispositivo(nome):
    for bruto in _carregar_bruto():
        if bruto["dispositivo"] == nome:
            return bruto
    return None

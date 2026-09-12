<div align="center">

# Digital Twins para a Organização de Operações em Centros Logísticos

### Simulação de Gêmeo Digital para eliminar "contêineres fantasma" em operações de remanejamento

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Digital Twin Framework](https://img.shields.io/badge/Digital_Twin_Framework-Leite_et_al.-7F5AF0?style=for-the-badge)
[![Artigo Completo](https://img.shields.io/badge/📄_Artigo_Completo-PDF-7F5AF0?style=for-the-badge)](./Paper.pdf)

</div>

---

## Sobre o projeto

Projeto desenvolvido na disciplina de **Prática em Pesquisa** (PUCRS), com o objetivo de reproduzir um estudo de pós-graduação sobre a aplicação de **Gêmeos Digitais (Digital Twins)** em centros logísticos.

Em operações de remanejamento (*rehandling*) — quando contêineres superiores precisam ser removidos para liberar acesso aos inferiores — erros humanos no registro da nova posição de uma carga geram **"contêineres fantasma"**: unidades cuja localização física deixa de coincidir com o que está registrado no sistema. Segundo a ABRAPPE (2023), falhas operacionais desse tipo causam um prejuízo estimado em **R$ 3,36 bilhões por ano** ao mercado brasileiro.

Este projeto propõe reduzir esses eventos através de uma arquitetura de Digital Twin: um modelo virtual continuamente sincronizado com o ambiente físico, que atua como guia inteligente para os operadores e evita erros de posicionamento durante o remanejamento.

>  O projeto foi apresentado em pitch a um diretor da **Hewlett-Packard (HP)** e resultou no artigo científico completo, disponível neste repositório em [`Paper.pdf`](./Paper.pdf).

## Arquitetura da solução

A solução foi estruturada em três camadas:

1. **Modelagem do ambiente físico** — representação digital do centro logístico através de três entidades principais: **edifícios** (posição, identificação RFID e capacidade máxima de empilhamento), **contêineres** (identificação, posição tridimensional e edifício associado) e a **empilhadeira** (localização, tarefa em execução e estado operacional). O ambiente também modela uma área de entrega, uma área de armazenamento temporário no solo e uma base operacional.
2. **Simulação de sensores e eventos** — algoritmos que geram as leituras RFID (edifícios e contêineres) e os eventos operacionais correspondentes.
3. **Máquina de estados finitos** — coordena as etapas executadas pela empilhadeira: deslocamento, validação RFID, remanejamento de cargas, verificação de capacidade, reorganização, entrega do contêiner e retorno à base.

A comunicação entre as camadas ocorre pelo estado das entidades armazenadas no próprio Digital Twin, permitindo que os algoritmos compartilhem informação continuamente. Os eventos gerados também são exportados em JSON via HTTP para um serviço externo, possibilitando o acompanhamento das operações em tempo real.

## Algoritmos do repositório

| Script | Responsabilidade |
|---|---|
| `forklift_simulating_movement.py` | Controla a navegação da empilhadeira: calcula a distância euclidiana até o destino (edifício de origem, armazenamento temporário, área de entrega, solo ou base) e atualiza sua posição a cada execução |
| `containers_rfid_reader.py` | Simula a leitura RFID de contêineres: identifica os contêineres do edifício validado, sua posição na pilha e se há unidades acima do alvo, calculando distância e força de sinal (RSSI) |
| `building_rfid_reader.py` | Simula a leitura RFID de identificação do edifício: calcula a intensidade do sinal em função da distância e valida qual estrutura está sendo acessada pela empilhadeira |
| `building_capacity_monitor.py` | Verifica a ocupação de cada edifício frente à capacidade máxima e identifica contêineres excedentes — o mecanismo central de **detecção de contêineres fantasma** |
| `stock_request.py` | Gera requisições sintéticas de movimentação de estoque, disparando o deslocamento da empilhadeira até o contêiner solicitado |

Esses algoritmos rodam sobre o framework de Gêmeos Digitais (pacote `Centro_Logistico.dtpkg`), desenvolvido por Leite et al. — um framework genérico e orientado a metadados que abstrai a complexidade de infraestrutura de TI por meio de configurações declarativas, permitindo testar cenários de erro sem necessidade de dispositivos físicos reais.

## Resultados

- A localização dos contêineres passou a ser **atualizada automaticamente** a cada evento RFID, eliminando a necessidade de registro manual de movimentações — a principal causa da divergência entre o mundo físico e os sistemas de controle.
- O sistema identificou em tempo real situações de **violação de capacidade** (excesso de contêineres acima do limite de um edifício), gerando alertas e realocando automaticamente as unidades excedentes para edifícios com maior espaço livre.
- A sincronização contínua entre ambiente físico e virtual se manteve consistente mesmo em cenários com múltiplas operações de remanejamento simultâneas, preservando a rastreabilidade da carga do início ao fim da operação.

## Trabalhos futuros

O artigo aponta como próximos passos: permitir mais de um contêiner alocado temporariamente no solo, viabilizar remanejamento em áreas de borda da rua, e validar a arquitetura em um ambiente físico real com sensores IoT e hardware de telemetria.

## Estrutura do repositório

```
├── Algoritmos_Geracao/
│   ├── forklift_simulating_movement.py
│   ├── containers_rfid_reader.py
│   ├── building_rfid_reader.py
│   ├── building_capacity_monitor.py
│   └── stock_request.py
├── Centro_Logistico.dtpkg        # Pacote do experimento no DT Framework
├── Modelagem_Empilhadeira.pdf    # Modelagem da máquina de estados da empilhadeira
├── Paper.pdf                     # Artigo científico completo do projeto
└── Video_Funcionamento.mp4       # Vídeo com resultado do experimento
```

## Créditos

- **Liderança:** Marco Antônio De Carli Rodegheri — apresentação do pitch final.
- **Equipe de pesquisa:** Bernardo Garcia, Lucas Lorenzi, Luiz H. S. Confortin, Roger R. Ehlert
- **Orientação:** Prof. Fabiano Hessel (PUCRS)
- **Framework de Digital Twin:** desenvolvido por Alex E. G. Leite, J. Venturini e F. Hessel — *"A Generic and Extensible Digital Twin Framework for Industrial IoT Environments"* (AINA, 2026)

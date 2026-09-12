<div align="center">

# Gêmeos Digitais em Centros Logísticos

### Simulação de Digital Twin aplicada à operação de remanejamento de contêineres

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Concluído-success?style=for-the-badge)
![PUCRS](https://img.shields.io/badge/PUCRS-Prática_em_Pesquisa-00d9ff?style=for-the-badge)

</div>

---

## Sobre o projeto

Projeto desenvolvido na disciplina de **Prática em Pesquisa** (PUCRS), com o objetivo de reproduzir um estudo de pós-graduação sobre a aplicação de **Gêmeos Digitais (Digital Twins)** em centros logísticos.

O desafio central era mitigar a ocorrência de **"contêineres fantasma"** — situação causada por erros humanos, que desorganiza inventários e localizações de contêineres durante a operação de remanejamento (*rehandling*), gerando inconsistências críticas em portos, galpões e armazéns.

A solução utiliza um framework de Gêmeos Digitais como ferramenta de auxílio em tempo real para os operadores, impedindo que erros ocorram no momento de atualizar as novas posições dos contêineres remanejados — trazendo mais segurança, previsibilidade e eficiência para a operação.

>  O projeto foi apresentado em pitch a um diretor da **Hewlett-Packard (HP)**, além de ter resultado em um artigo científico completo (disponível neste repositório em [`Paper.pdf`](./Paper.pdf)).

## Como funciona

O repositório contém os algoritmos de geração de dados sintéticos que alimentam a simulação do Digital Twin, cada um responsável por replicar o comportamento de um componente real do centro logístico:

| Script | Responsabilidade |
|---|---|
| `forklift_simulating_movement.py` | Simula a movimentação da empilhadeira entre a área base, a área de picking e o solo, incluindo a máquina de estados do equipamento |
| `containers_rfid_reader.py` | Simula a leitura RFID de contêineres pela empilhadeira, calculando distância e força de sinal (RSSI) em tempo real |
| `building_rfid_reader.py` | Simula a leitura RFID de identificação do galpão/armazém em que a empilhadeira está operando |
| `building_capacity_monitor.py` | Monitora a ocupação de cada galpão e identifica contêineres em excesso acima da altura máxima permitida — o núcleo da detecção de inconsistências |
| `stock_request.py` | Gera requisições sintéticas de movimentação de estoque, disparando o deslocamento da empilhadeira até o contêiner solicitado |

Esses algoritmos rodam sobre o framework de Gêmeos Digitais (pacote `Centro_Logistico.dtpkg`), que mantém o estado consolidado de cada instância (empilhadeira, contêineres, galpões) e permite consultar e atualizar esse estado em tempo real — permitindo testar cenários de erro sem necessidade de dispositivos físicos reais.

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
└── Paper.pdf                     # Artigo científico completo do projeto
```

## Créditos

- **Liderança e desenvolvimento:** Marco Antônio De Carli Rodegheri — concepção das ideias, abordagem e execução da pesquisa, redação científica, coordenação do planejamento e das entregas da equipe, e apresentação do pitch final.
- **Orientação:** Prof. Fabiano Hessel (PUCRS)
- **Agradecimento especial:** ao mestrando **Alex Elias**, que disponibilizou o framework que possibilitou a simulação do Digital Twin sem necessidade de dispositivos físicos reais.

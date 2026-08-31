# Roteiro da reunião: Open RAN, Nephio, xApps e laboratório multi-UE

Objetivo: apresentar em 15 a 20 minutos uma POC acadêmica funcionando, provar os
resultados ao vivo e terminar com uma proposta clara de uso por alunos.

## Antes da reunião

- Conecte a VPN institucional do NMI.
- Abra a apresentação e deixe o PDF disponível como material de apoio.
- Abra em abas:
  - Open5GS WebUI: `http://192.168.72.10:30454`;
  - Grafana: `http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview`;
  - logs: `http://192.168.72.10:30300/d/oran-logs/o-ran-kubernetes-logs`;
  - painel CIC: `http://192.168.72.10:30300/d/oran-multisite/cic-arm-lab`;
  - Alertmanager: `http://192.168.72.10:30301`.
- Abra a Web UI do Nephio com o túnel abaixo e acesse
  `http://127.0.0.1:7007/config-as-data`:

```bash
ssh -L 7007:127.0.0.1:7007 -t lucasrc@192.168.72.10 \
  'kubectl -n nephio-webui port-forward --address=127.0.0.1 service/nephio-webui 7007:7007'
```

- Em outro terminal, entre no control plane:

```bash
ssh lucasrc@192.168.72.10
cd /home/lucasrc/oran-stack-main
```

## Abertura — 40 segundos

> “O que montamos não é apenas um monte de pods. É uma bancada Open RAN
> reproduzível: temos Core 5G, RAN simulada, Near-RT RIC, xApps, Nephio/GitOps,
> observabilidade e um segundo cluster ARM. O aluno consegue alterar um
> algoritmo, publicar a xApp, gerar tráfego de um UE e enxergar a consequência
> no Grafana.”

Em seguida, deixe explícito:

> “Isto é laboratório e pesquisa, não produção. Priorizamos experimentação,
> visibilidade e repetibilidade; não alta disponibilidade pela alta
> disponibilidade.”

## Parte 1 — A arquitetura em 3 minutos

Use os slides 2 a 5.

Fale nesta ordem:

1. O NMI tem cinco nós Kubernetes `amd64`: VM 105, VM 111, VM 112, VM 113 e
   `nmi-srv03`.
2. A VM 105 mantém Open5GS, CU/DU, srsUE e o RIC base; a VM 111 termina E2; a
   VM 112 hospeda as xApps; a VM 113 hospeda Nephio/Porch; o Dell concentra a
   observabilidade.
3. O CIC é outro cluster, com dois nós Ampere `arm64`, e executa a mesma imagem
   multiarch da `r4-simple-mon`.
4. Kubernetes move e conecta pods; Near-RT RIC recebe telemetria/controle da
   RAN; Nephio especializa pacotes; Flux reconcilia o estado nos clusters.
5. O tráfego do usuário não passa pelo RIC: `UE → DU/CU → UPF → Internet`. O
   RIC recebe KPM pela interface E2.

Prova rápida do NMI, no terminal já conectado:

```bash
sudo kubectl get nodes -o wide
```

Prova do CIC, em um segundo terminal local no notebook:

```bash
ssh -J lucasrc@192.168.72.10 lucasrc@192.168.0.210 \
  'sudo kubectl get nodes -o wide'
```

Resultado esperado: `5/5 Ready` no NMI e `2/2 Ready` no CIC.

## Parte 2 — O que a xApp faz em 2 minutos

Use os slides 6 a 8.

> “A `simple-mon` não controla a RAN. Ela assina `DRB.UEThpDl`, recebe
> indicações E2SM-KPM pelo RMR e exporta a série para Prometheus. A
> `kpm-load-watch` usa o mesmo fluxo, calcula uma média móvel e classifica o
> rádio em `idle`, `active` ou `busy`. Portanto o algoritmo do aluno fica
> observável.”

Explique KPI em uma frase:

> “KPI é um indicador de desempenho; neste caso, throughput downlink observado
> no O-DU.”

Ressalva importante:

> “O Report Style atual é agregado no O-DU. Enxergamos carga do rádio, mas ainda
> não atribuímos o valor a um IMSI específico.”

## Parte 3 — Nephio sem mistério em 2 minutos

Use os slides 14 e 15 e abra a Web UI.

> “Nephio não é Rancher, OpenShift, Helm ou RIC. O objeto central é um pacote de
> configuração. O Team Blueprint descreve a xApp reutilizável; a
> PackageVariant especializa site, arquitetura, imagem e endpoints; Porch
> publica a revisão; Git registra a intenção; Flux aplica no cluster.”

Mostre na Web UI:

- `simple-mon-nmi-v5`;
- `simple-mon-cic-arm64`;
- `kpm-load-watch-nmi`.

Comandos de evidência:

```bash
sudo kubectl get packagevariants -A
sudo kubectl -n flux-system get kustomizations
sudo kubectl -n ricxapp get deploy,pod -o wide
```

Frase-chave:

> “Nephio publica configuração; ele não executa a xApp. Kubernetes executa o
> pod e Flux fecha o caminho GitOps.”

## Parte 4 — Demonstração ao vivo em 5 minutos

Deixe o painel Grafana aberto e execute no control plane NMI:

```bash
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-ue-lab.sh ue2
```

Enquanto o script roda, narre:

1. Os três assinantes já existem no Open5GS; o script seleciona o perfil UE2.
2. O srsUE registra, autentica e estabelece a sessão PDU.
3. `tun_srsue` recebe um endereço `10.45.0.x`.
4. Uma transferência limitada a 50 MB atravessa RAN, UPF e NAT.
5. A xApp observa `idle → active/busy → idle`.
6. O aceite exige HTTP 200 e termina em `UE_LAB_DEMO_OK`.

Depois repita, se houver tempo:

```bash
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-ue-lab.sh ue3
```

Não prometa endereços fixos `.18` ou `.19`: diga `10.45.0.x`, pois o endereço
pode mudar entre sessões.

## Parte 5 — A prova ARM em 1 minuto

Abra o painel CIC e diga:

> “Não recompilamos uma xApp diferente para o CIC. Publicamos um índice
> multiarch, fixamos o mesmo digest e o registry entrega `amd64` no NMI e
> `arm64` no CIC. O pod ARM mantém uma assinatura KPM e já recebeu mais de mil
> indicações.”

Se quiser executar a verificação completa:

```bash
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/demo-kpm-multisite.sh
```

## Fechamento — 40 segundos

Use os slides 16 e 17.

> “A infraestrutura deixou de ser o experimento e virou a bancada. O próximo
> experimento é didático: um aluno cria uma nova xApp pelo scaffold, publica a
> imagem multiarch, gera uma PackageVariant, entrega por Flux, dispara UE2 ou
> UE3 e explica a evidência no Grafana. A partir daí podemos estudar KPI por UE,
> rádio e SIM físicos, algoritmos novos e E2SM-RC.”

Última frase:

> “O objetivo não é dizer que temos uma operadora pronta. É mostrar que temos
> um laboratório onde uma hipótese sobre a RAN vira código, simulação e
> evidência reproduzível.”

## Perguntas previsíveis

### “Nephio é um Rancher?”

Não. Rancher/OpenShift administram a plataforma Kubernetes. Nephio trabalha
com pacotes e variantes de funções de rede; nesta POC, Flux aplica o resultado.

### “Por que Nephio está no mesmo cluster?”

Porque o objetivo é laboratório. Namespaces, RBAC e afinidade já separam a
gestão na VM 113. Um cluster extra aumentaria manutenção sem melhorar o
experimento atual.

### “Temos três UEs simultâneos?”

Não. Temos três perfis de assinante testáveis em sequência. O enlace ZMQ atual
possui um único peer RF. Simultaneidade exige rádio real ou emulação RF
multi-UE apropriada.

### “A xApp sabe qual assinante gerou o tráfego?”

Ainda não. O KPM atual é agregado no O-DU. KPI por UE é uma linha de pesquisa
separada, dependente de Report Style e suporte da RAN.

### “A xApp controla a RAN?”

As atuais não. Elas monitoram. Um closed loop exigirá lógica de decisão,
E2SM-RC, limites de segurança e testes.

### “Por que usar ARM no CIC?”

Para provar portabilidade de workloads de edge e o fluxo de variantes por
arquitetura. A mesma base de código e o mesmo digest atendem `amd64` e `arm64`.

### “Isso está pronto para produção?”

Não é o objetivo. É uma POC acadêmica com control plane único, storage simples
e retenção curta. Isso é uma escolha consciente do laboratório.

## Plano B se a demo ao vivo falhar

1. Não reinicie a pilha inteira na frente da banca.
2. Mostre o slide 9, os dashboards e as três PackageVariants.
3. Mostre o histórico de métricas e o estado atual:

```bash
sudo kubectl get nodes
sudo kubectl -n near-rt-ric get pods
sudo kubectl -n ran get pods
sudo kubectl -n ricxapp get pods
sudo kubectl -n flux-system get kustomizations
```

4. Explique que `demo-ue-lab.sh` é o teste idempotente e que o aceite já foi
   repetido para UE2 e UE3 com HTTP 200 e KPM.
5. Se apenas a Web UI do Nephio falhar, mostre `PackageVariant`, Porch e Flux
   pelo terminal: a UI é visualização; o fluxo declarativo continua sendo a
   evidência real.

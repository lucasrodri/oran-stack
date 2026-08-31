# Laboratório: criar e entregar uma nova xApp KPM

Este roteiro ensina um aluno a criar uma xApp de monitoramento, publicá-la como
imagem `amd64/arm64`, transformá-la em um Team Blueprint do Nephio, implantá-la
no NMI pelo fluxo Porch/Git/Flux e provar o resultado com tráfego real do UE
simulado. É um laboratório e não um procedimento de produção.

Tempo esperado: 60 a 90 minutos depois que o ambiente base estiver saudável.

## 1. O que o aluno está construindo

```text
código Python -> imagem multiarch por digest -> Team Blueprint
       -> PackageVariant NMI -> Porch Published -> Git NMI -> Flux
       -> Pod xApp -> AppMgr/RTMgr/SubMgr -> E2Term -> O-DU simulado
       -> /metrics -> Prometheus -> Grafana
```

A xApp não configura o SIM, não registra o UE no Open5GS e não substitui o RIC.
Ela pede uma assinatura E2SM-KPM ao SubMgr, recebe indicações pelo RMR e executa
o algoritmo escrito pelo aluno. `xAppBase` já cuida do registro no AppMgr, da
resposta HTTP da assinatura, do loop RMR e das métricas Prometheus.

O primeiro deploy deve ser no cluster NMI. O deploy no CIC é uma etapa avançada
e assistida pela equipe de infraestrutura: cada xApp remota precisa de
NodePorts e bridges RMR exclusivos. O aluno não deve inventar portas no pfSense.

## 2. Pré-requisitos e aceite do ambiente

- VPN do NMI conectada.
- Branch criada a partir de `main` atualizado.
- gNB `gnbd_001_001_00019b_e2` conectado ao E2Mgr.
- RAN e UE simulados saudáveis.
- acesso ao repositório, ao GitHub Actions e ao worker Nephio.
- nome DNS único, em minúsculas, por exemplo `kpm-latency-lab`.

Verifique o estado antes de programar:

```bash
ssh lucasrc@192.168.72.10
sudo kubectl -n near-rt-ric get pods
sudo kubectl -n ran get pods
curl -fsS http://127.0.0.1:30380/v1/nodeb/states
```

Critério: E2Term Ready, O-DU conectado e UE Ready. Não continue mascarando uma
falha da pilha base como se fosse um erro da xApp.

## 3. Gerar o scaffold

Na cópia local do repositório:

```bash
git switch -c aluno/kpm-latency-lab
./scripts/new-kpm-xapp.sh kpm-latency-lab DRB.UEThpDl 2000
```

O comando cria cinco partes:

| Artefato | Função |
|---|---|
| `xapps/python/kpm_latency_lab_xapp.py` | código executado no container |
| `packages/nephio/kpm-latency-lab/` | Team Blueprint reutilizável |
| `infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml` | especialização NMI |
| `infra/nephio/nmi-onboarding/kpm-latency-lab-rbac.yaml` | identidade Flux restrita |
| `infra/nephio/nmi-onboarding/kpm-latency-lab-flux-sync.yaml` | reconciliação do pacote |

O gerador se recusa a sobrescrever uma xApp existente. Ele deixa
`REPLACE_WITH_MULTIARCH_IMAGE_DIGEST` de propósito: o digest só existe depois
do primeiro build.

O último argumento é o período KPM em milissegundos. Use um período diferente
das xApps concorrentes que pedem a mesma métrica (`r4-simple-mon` NMI usa
`1000`, por exemplo). Solicitações idênticas podem ser fundidas pelo SubMgr na
mesma assinatura E2; para um experimento independente, métrica ou período devem
ser distintos.

## 4. Programar o comportamento

Abra o arquivo Python gerado. O método `indication_callback` é o ponto de
extensão. O scaffold já recebe Report Style 1 e exporta automaticamente:

- `oran_xapp_active_subscriptions`;
- `oran_xapp_rmr_indications_total`;
- `oran_xapp_kpm_indications_total`;
- `oran_xapp_kpm_measurement`;
- `oran_kpm_drb_ue_throughput_dl_kbps` para `DRB.UEThpDl`.

Comece com uma mudança pequena e mensurável: média móvel, limiar, classificação
de estado ou novo contador. Não envie uma ação de controle RAN no primeiro
experimento. Mantenha o callback rápido e não bloqueante.

O template imprime apenas a primeira indicação e uma a cada 30. Não grave uma
linha por KPM em operação normal; Prometheus é a representação durável dos
valores e os logs do laboratório têm retenção curta.

Validação estática antes do build:

```bash
python3 -m py_compile xapps/python/kpm_latency_lab_xapp.py
bash -n scripts/new-kpm-xapp.sh
rg 'REPLACE_WITH_MULTIARCH_IMAGE_DIGEST' \
  packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml
git diff --check
```

## 5. Construir e fixar a imagem multiarch

O arquivo `Dockerfile.xapps` copia toda a pasta `xapps/python/`. Portanto, o
novo script entra na imagem laboratorial comum; não é necessário criar um
Dockerfile por aluno.

```bash
git add xapps/python/kpm_latency_lab_xapp.py \
  packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml \
  infra/nephio/nmi-onboarding/kpm-latency-lab-rbac.yaml \
  infra/nephio/nmi-onboarding/kpm-latency-lab-flux-sync.yaml
git commit -m "feat(xapp): add kpm latency laboratory monitor"
git push -u origin aluno/kpm-latency-lab
```

O workflow `Build multi-architecture laboratory xApps` deve confirmar
`linux/amd64` e `linux/arm64`. Depois do build, copie o digest do índice, nunca
o digest de apenas uma plataforma. A referência final tem este formato:

```text
ghcr.io/lucasrodri/oran-stack/oran-xapps@sha256:<64-hex-digits>
```

Substitua o marcador nos dois arquivos:

```bash
IMAGE='ghcr.io/lucasrodri/oran-stack/oran-xapps@sha256:<digest-do-indice>'
sed -i.bak "s#REPLACE_WITH_MULTIARCH_IMAGE_DIGEST#${IMAGE}#" \
  packages/nephio/kpm-latency-lab/workload-cluster.yaml \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml
rm packages/nephio/kpm-latency-lab/workload-cluster.yaml.bak \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml.bak
rg 'REPLACE_WITH|:latest' packages/nephio/kpm-latency-lab \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml
```

O último `rg` deve retornar vazio. Faça commit e push do digest.

## 6. Publicar o Team Blueprint e gerar o pacote NMI

No worker Nephio, com um checkout do mesmo commit:

```bash
ssh lucasrc@192.168.71.30
cd /caminho/para/oran-stack
export KUBECONFIG=/etc/nephio/nmi-admin.conf

sudo -E ./infra/nephio/blueprints/publish-xapp-blueprint.sh \
  kpm-latency-lab packages/nephio/kpm-latency-lab v1

sudo -E kubectl apply -f \
  infra/nephio/blueprints/kpm-latency-lab-nmi-variant.yaml
sudo -E ./infra/nephio/blueprints/approve-packagevariant.sh \
  kpm-latency-lab-nmi
```

O resultado esperado é:

```text
team-blueprints.kpm-latency-lab.v1             Published
nmi.kpm-latency-lab-nmi.packagevariant-1      Published
```

Porch publica configuração; ele não executa o código da xApp. O commit criado
no repositório de deployment `nmi` é a entrada consumida pelo Flux.

## 7. Entregar com uma identidade Flux restrita

Ainda no worker Nephio:

```bash
sudo -E kubectl apply -f \
  infra/nephio/nmi-onboarding/kpm-latency-lab-rbac.yaml
sudo -E kubectl apply -f \
  infra/nephio/nmi-onboarding/kpm-latency-lab-flux-sync.yaml

sudo -E kubectl -n flux-system wait \
  kustomization/kpm-latency-lab \
  --for=condition=Ready --timeout=300s
```

A identidade pode gerenciar apenas Deployment, Service e ConfigMap em
`ricxapp`; ela não recebe acesso a Secrets, RAN ou Core.

## 8. Aceite funcional da xApp

No control plane NMI:

```bash
sudo kubectl -n ricxapp rollout status deployment/kpm-latency-lab \
  --timeout=180s
sudo kubectl -n ricxapp get pod,service -l app=kpm-latency-lab -o wide

curl -fsS http://127.0.0.1:30080/ric/v1/xapps | \
  grep -F 'kpm-latency-lab'

sudo kubectl -n ricxapp exec deployment/kpm-latency-lab -c xapp -- \
  curl -fsS http://127.0.0.1:8091/metrics | \
  grep -E '^oran_xapp_(active_subscriptions|rmr_indications_total|kpm_indications_total)'
```

Critérios:

- Pod Ready e sem restart crescente;
- AppMgr contém a xApp em `service-ricxapp-kpm-latency-lab-rmr:4561`;
- `active_subscriptions 1`;
- os contadores RMR e KPM aumentam entre duas leituras;
- RTMgr não registra falha ao atualizar a rota dessa xApp.

Prometheus descobre qualquer Service `ricxapp` com `monitoring="true"`. No
Grafana, abra pela VPN NMI:

- `http://192.168.72.10:30300/d/oran-overview/o-ran-stack-overview`

O painel separa as séries pelo label `service`, permitindo comparar a xApp nova
com `r4-simple-mon`.

## 9. Gerar tráfego do UE e observar o KPI

O script existente aceita a xApp por variável de ambiente:

```bash
cd /home/lucasrc/oran-stack-main
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  XAPP_DEPLOYMENT=kpm-latency-lab ./scripts/demo-kpm.sh
```

Ele transfere um arquivo limitado pela interface `tun_srsue`, atravessa
UE -> O-DU/O-CU -> UPF -> Internet e consulta o KPI durante o tráfego. Aceite:
HTTP 200, pico `DRB.UEThpDl` maior que zero e `DEMO_KPM_OK`.

Este primeiro laboratório usa um UE. O experimento com múltiplos UEs exige
IMSI/chaves distintos no Open5GS, configurações UE separadas e ZMQ/recursos de
rádio coerentes; ele deve ser tratado como um roteiro próprio, não como cópia
do mesmo SIM.

## 10. Atualização e rollback

Uma atualização é uma nova revisão imutável:

1. altere o algoritmo e adicione um teste;
2. gere uma nova imagem e fixe o novo digest;
3. crie `v2` copiando a revisão anterior;
4. atualize o `PackageVariant` para `workspaceName: v2`;
5. aprove o novo downstream package;
6. espere Flux Ready e repita o teste KPM.

Rollback também é para frente: copie o conteúdo conhecido de `v1` para uma
nova revisão `v3-rollback`. Não faça `git reset`, não mova tags publicadas e não
edite um PackageRevision já Published.

## 11. Falhas comuns

| Sintoma | Verificação principal |
|---|---|
| init container esperando | E2 node ausente ou `DISCONNECTED` no E2Mgr |
| AppMgr tem a xApp, assinatura falha | endpoint/nome de Service não coincide com o registro |
| assinatura ativa, KPM zero | UE ocioso ou métrica não implementada pelo E2 node escolhido |
| duas xApps compartilham o mesmo ID e só uma recebe | métrica e período idênticos; use período distinto |
| RMR não recebe indicação | RTMgr, rota `12050`, porta `4561` e subscription ID |
| Flux `Ready=False` | caminho Git, RBAC, imagem/digest ou manifesto inválido |
| imagem funciona no NMI, não no CIC | índice sem `linux/arm64` ou dependência nativa não portada |
| Grafana `No Data` | Service sem `monitoring=true`, target Prometheus down ou scrape recente |

## 12. Checklist para entrega do aluno

- [ ] código e objetivo da xApp documentados;
- [ ] logs limitados e nenhum segredo no código;
- [ ] imagem `amd64/arm64` fixada pelo digest do índice;
- [ ] Team Blueprint e PackageVariant publicados;
- [ ] Flux Ready usando ServiceAccount restrita;
- [ ] AppMgr, assinatura e RMR validados;
- [ ] contadores KPM crescendo;
- [ ] experimento de tráfego reproduzível;
- [ ] atualização e rollback demonstrados;
- [ ] gráfico ou tabela com hipótese, estímulo e resultado.

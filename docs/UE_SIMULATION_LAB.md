# Laboratório de múltiplos perfis UE

O laboratório atual simula três assinantes Open5GS e três identidades de
aparelho, mas usa uma identidade por vez no único enlace de rádio ZMQ. Isso é
equivalente a trocar o SIM/aparelho ligado ao rádio virtual da bancada.

```text
UE1 / UE2 / UE3 (perfis) -- um por vez --> srsUE -- ZMQ --> O-DU/O-CU
       |                                             |
       +--> Open5GS (autenticação e PDU)              +--> E2/KPM --> xApps
```

Não escale o Deployment `srsue` para três réplicas. O DU atual oferece um único
par `tx_port/rx_port` ZMQ; réplicas concorrentes não representam três rádios e
produzem uma topologia inválida. Dois UEs ao mesmo tempo usam o broker de IQ
descrito abaixo, com `zmq.broker.enabled=true`. Sem esse broker, o laboratório
continua com um único peer.

## Perfis

| Perfil | IMSI | IMEI | Uso |
|---|---|---|---|
| `ue1` | `001010000000001` | `353490069873319` | referência |
| `ue2` | `001010000000002` | `353490069873320` | aluno/experimento A |
| `ue3` | `001010000000003` | `353490069873321` | aluno/experimento B |

Os três perfis reaproveitam as credenciais laboratoriais K/OPc do assinante
base. A clonagem ocorre somente dentro do MongoDB: os scripts não imprimem nem
gravam as chaves. Em um teste com SIMs físicos, cada SIM deve ter seu próprio
K/OPc e provisionamento seguro.

## Demonstração em um comando

No control plane NMI, a partir de um checkout atualizado:

```bash
sudo env KUBECONFIG=/etc/kubernetes/admin.conf ./scripts/demo-ue-lab.sh ue2
```

O comando:

1. cria/atualiza os três assinantes no Open5GS de forma idempotente;
2. para o peer UE anterior, injeta IMSI/IMEI no template sem mostrar K/OPc;
3. reabre somente o endpoint ZMQ do O-DU e inicia o novo srsUE;
4. aguarda a interface `tun_srsue` ganhar endereço;
5. renova as assinaturas das xApps de monitoramento após o novo E2 setup;
6. transfere somente 50 MB pelo user plane;
7. exige que `kpm-load-watch` observe `active`, `busy` e o retorno a `idle`.

Como o período KPM da xApp é de 3 segundos, a borda de subida pode saltar de
`idle` diretamente para `busy`; nesse caso, `active` aparece na queda da média
móvel. Isso é amostragem discreta normal, não perda do KPI.

Repita com `ue3` para demonstrar outro assinante. Para voltar ao perfil base:

```bash
sudo env KUBECONFIG=/etc/kubernetes/admin.conf \
  ./scripts/select-ue-lab-profile.sh ue1
```

O KPI atual (`DRB.UEThpDl`, Report Style 1) é agregado no O-DU. Portanto, a xApp
prova a carga do rádio, mas não atribui a medição a um IMSI. Identificação KPM
por UE usa o Report Style 4 e a chave `gNB-CU-UE-F1AP-ID`, não o IMSI.

## Dois UEs e a ação E2 de cota de PRB

O OCUDU 26.04 aceita um único RIC Control: E2SM-RC Style 2 Action 6 (cota de
PRB por UE). RRC Connection Release é Style 4 Action 4 e este RAN não o
implementa. A validação da ação E2 é zerar a cota de PRB do UE anômalo.

```text
srsue-ue1 (normal) --+
                     +--> zmq-broker (copia DL, soma UL) --> O-DU --> KPM Style 4
srsue-ue2 (anomalia) --+                                      ^
                                                              |
                                    kpm-anomaly-prb: Style 2 Action 6, max PRB 0
```

O modo de um UE permanece o padrão (`zmq.broker.enabled: false`). Para os dois
peers, no values do chart `ran`:

```yaml
zmq:
  broker:
    enabled: true
```

Isso sobe o broker e os Deployments `srsue-ue1` (IMSI `001010000000001`) e
`srsue-ue2` (IMSI `001010000000002`). O segundo UE espera 8 s a mais antes do
attach, para não usar a mesma ocasião de PRACH. O Deployment `srsue` único não
é criado nesse modo, e `select-ue-lab-profile.sh` continua valendo só para o
modo de um peer.

A xApp vai num release separado do chart genérico, sem substituir o
`r4-simple-mon`:

```bash
helm upgrade --install kpm-anomaly-prb helm/xapps/xapp \
  -f helm/xapps/xapp/values/kpm-anomaly-prb.yaml \
  --set xapp.e2NodeId=<e2_node_id do O-DU>
```

Ela assina `DRB.RlcPacketDropRateDl` no Report Style 4. Essa métrica do O-DU
é a taxa de descarte de SDU RLC no downlink ([Supported E2 Metrics](https://docs.ocudu.org/knowledge_base/e2sm_kpm_metrics/)).
Depois de ver dois `gNB-CU-UE-F1AP-ID`, envia Style 2 Action 6 uma vez para
cada UE cuja média móvel dessa taxa fique em ou acima de 1
(`min`/`max`/`dedicated` PRB = 0) e registra `RIC_CONTROL_ACK` ou
`RIC_CONTROL_FAILURE` para esse UE. O peer `ue2` apaga cerca de 5% dos
quadros de downlink (`lossRatio: 0.05`); `ue1` permanece com rádio limpo.

Como conferir, com os dois `tun_srsue` já estabelecidos:

```bash
sudo env KUBECONFIG=/etc/kubernetes/admin.conf ./scripts/demo-anomaly-prb.sh
```

O script não degrada o rádio de `srsue-ue1`. Ele faz um download limitado só
em `srsue-ue2`, para haver SDU RLC que possam ser descartados, imprime
`DRB.RlcPacketDropRateDl` por `ue_id` e exige `RIC_CONTROL_ACK` para o UE
cuja taxa subiu. `srsue-ue1` precisa continuar com `tun_srsue`. No Grafana:

```promql
oran_xapp_kpm_measurement{metric="DRB.RlcPacketDropRateDl",service="service-ricxapp-kpm-anomaly-prb-http"}
```

A série do `ue_id` anômalo sobe durante o download. A do UE normal permanece
em zero.

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
produzem uma topologia inválida. Para UEs simultâneos será necessário um rádio
real com capacidade multi-UE ou um emulador/broker RF apropriado.

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
por UE é uma evolução separada e depende de outro Report Style e do suporte da
implementação RAN.

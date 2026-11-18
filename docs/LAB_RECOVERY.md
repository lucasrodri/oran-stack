# Recuperação do laboratório Open RAN

Este procedimento é para interrupções de energia, rede, VPN ou reinicialização
de vários nós. Ele preserva dados e reinicia apenas componentes sem estado da
RAN simulada e do Near-RT RIC.

## Por que UE e E2 pareciam sensíveis

Não é a latência normal da rede que derruba a pilha. Há duas dependências de
ciclo de vida no laboratório:

1. A RU simulada usa ZMQ. O UE deve conectar ao endpoint da DU atual; depois de
   uma recriação da DU, uma sessão antiga do UE não se recupera sempre sozinha.
2. AppMgr e RTMgr mantêm inventário e rotas voláteis. Após uma queda parcial,
   o RTMgr pode iniciar antes das xApps ou conservar um endpoint remoto já
   indisponível. Nesse caso a subscription existe, mas a indicação não chega.

As xApps agora usam um único listener RMR na porta 4561. Elas recebem a
atualização de rota do RTMgr no próprio loop e devolvem o ACK padrão de tipo 22.
Isso elimina a disputa anterior entre dois listeners `SO_REUSEPORT`, que podia
entregar uma indicação KPM ao coletor interno em vez da aplicação.

## Procedimento após uma queda

Execute na VM 105 (`oran-k8s-01`):

```bash
cd ~/oran-stack-main
git pull --ff-only

# 1. Confira os nós e pods.
kubectl get nodes
kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded

# 2. Recupere a ordem DU -> UE e espere a PDU session.
KUBECONFIG=$HOME/.kube/config ./scripts/recover-ran-zmq.sh

# 3. Reconstrua inventário, rotas e subscriptions KPM.
# Use RESET_APPMGR=1 após uma queda geral ou quando houver endpoints antigos.
RESET_APPMGR=1 ./scripts/recover-ric-kpm.sh

# 4. Valide o plano de usuário e o KPI downlink.
kubectl -n ran exec deploy/srsue -c srsue -- \
  ping -I tun_srsue -c 3 10.45.0.1
./scripts/demo-kpm.sh
```

Resultado esperado:

- os cinco nós NMI em `Ready`;
- CU, DU e UE em `Running`;
- `tun_srsue` com endereço `10.45.0.x` e ping sem perda para `10.45.0.1`;
- O-DU `CONNECTED` no E2Mgr;
- uma subscription ativa em cada xApp;
- `DEMO_KPM_OK` e KPI maior que zero durante a transferência.

Use `RESET_APPMGR=0` quando apenas a DU ou o UE reiniciou e os endpoints do
AppMgr continuam válidos. O reset é apropriado no laboratório porque o AppMgr é
sem estado, mas ele remove temporariamente também o registro de uma xApp remota
do CIC; essa xApp deve registrar-se de novo quando o enlace CIC–NMI voltar.

## CU aparece DISCONNECTED após reinício do E2Term

Na versão OCUDU usada no laboratório, a CU pode manter o processo vivo após
perder o E2 e não refazer a associação. `Running` e o teste de processo da
readiness probe não comprovam que o E2 voltou. Em 18/11/2026 o log da CU
registrava `E2 connection was closed` desde o reinício do E2Term em 12/11.

Na VM 105, confirme primeiro que o E2Term atual está registrado:

```bash
kubectl -n near-rt-ric exec deploy/ric-e2mgr -c e2mgr -- \
  curl -fsS http://localhost:3800/v1/e2t/list
```

Com um `e2tAddress` válido, recupere na ordem CU → DU → UE:

```bash
kubectl -n ran scale deploy/srsue deploy/ocudu-du --replicas=0
kubectl -n ran wait --for=delete pod -l app=srsue --timeout=120s
kubectl -n ran wait --for=delete pod -l app=ocudu-du --timeout=120s
kubectl -n ran delete pod -l app=ocudu-cu
kubectl -n ran rollout status deploy/ocudu-cu --timeout=180s

# Só prossiga quando a CU estiver CONNECTED neste inventário.
curl -fsS http://127.0.0.1:30380/v1/nodeb/states

kubectl -n ran scale deploy/ocudu-du --replicas=1
kubectl -n ran rollout status deploy/ocudu-du --timeout=180s
kubectl -n ran scale deploy/srsue --replicas=1
kubectl -n ran rollout status deploy/srsue --timeout=180s

# Pod Ready pode anteceder a PDU session. Espere o endereço do túnel.
for tentativa in $(seq 1 24); do
  if kubectl -n ran exec deploy/srsue -c srsue -- \
      ip -4 -o address show dev tun_srsue 2>/dev/null | grep -q 'inet '; then
    break
  fi
  sleep 3
done
kubectl -n ran exec deploy/srsue -c srsue -- \
  ping -I tun_srsue -c 3 -W 2 10.45.0.1

# Renove as subscriptions ligadas à associação anterior da DU.
kubectl -n ricxapp delete pod -l 'app in (r4-simple-mon,kpm-load-watch,kpm-mon-tmt)'
```

Na VM 120, recrie também o pod `r4-simple-mon` do CIC e execute
`infra/nephio/cic-onboarding/verify-cic-xapp.sh`. Confirme CU **e** DU
`CONNECTED`, contadores KPM avançando e o aceite `DEMO_KPM_MULTISITE_OK`
antes de considerar a recuperação concluída. O procedimento não exige
reiniciar novamente o E2Term.

## Quando o CIC volta depois do NMI

Confirme primeiro que a VM 105 alcança `192.168.0.211:30691/metrics` e que o
Flux CIC aplicou o runtime com `_ack_route_table_update`. Execute na VM 120:

```bash
# Recria o pod sem mudar o template administrado pelo Flux.
kubectl -n ricxapp delete pod -l app=r4-simple-mon
kubectl -n ricxapp rollout status deploy/r4-simple-mon --timeout=180s
```

Na VM 105, confirme o registro `r4-simple-mon-cic` no AppMgr e atualize o
inventário do RTMgr:

```bash
curl -fsS http://127.0.0.1:30080/ric/v1/xapps
kubectl -n near-rt-ric rollout restart deploy/ric-rtmgr
kubectl -n near-rt-ric rollout status deploy/ric-rtmgr --timeout=180s
```

Na VM 120, recrie novamente somente o pod da xApp para abrir sua assinatura
com o inventário pronto. Depois execute o verificador:

```bash
kubectl -n ricxapp delete pod -l app=r4-simple-mon
kubectl -n ricxapp rollout status deploy/r4-simple-mon --timeout=180s
bash infra/nephio/cic-onboarding/verify-cic-xapp.sh
```

Na VM 105, `./scripts/demo-kpm-multisite.sh` deve terminar com
`DEMO_KPM_MULTISITE_OK`. Se a DU também reiniciou, renove primeiro as xApps
locais com `./scripts/refresh-kpm-xapps.sh` e depois a xApp CIC. Use os
scripts a partir de um checkout atualizado do repositório.

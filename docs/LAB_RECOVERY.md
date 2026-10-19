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

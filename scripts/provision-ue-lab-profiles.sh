#!/usr/bin/env bash
set -euo pipefail

# Provision three deterministic laboratory subscriber identities in Open5GS.
# Authentication material is cloned inside MongoDB from the Vault-backed base
# subscriber and is never printed or copied to the local filesystem.

CORE_NAMESPACE="${CORE_NAMESPACE:-5g-core}"
MONGODB_POD="${MONGODB_POD:-mongodb-0}"

kubectl_args=()
if [[ -n "${KUBECONFIG:-}" ]]; then
  kubectl_args+=(--kubeconfig "${KUBECONFIG}")
fi

kctl() {
  kubectl "${kubectl_args[@]}" "$@"
}

read -r -d '' mongo_script <<'JS' || true
const baseImsi = '001010000000001';
const profiles = [
  { imsi: '001010000000001', msisdn: '+82100000001' },
  { imsi: '001010000000002', msisdn: '+82100000002' },
  { imsi: '001010000000003', msisdn: '+82100000003' }
];

const base = db.subscribers.findOne({ imsi: baseImsi });
if (!base || !base.security || !base.security.k || !base.security.opc) {
  throw new Error('Vault-backed base subscriber is missing or incomplete');
}

for (const profile of profiles) {
  const document = Object.assign({}, base, profile);
  delete document._id;
  document.security = Object.assign({}, base.security, { sqn: NumberLong('0') });
  document.updated_at = new Date();
  db.subscribers.updateOne(
    { imsi: profile.imsi },
    { $set: document },
    { upsert: true }
  );
}

printjson(db.subscribers.find(
  { imsi: { $in: profiles.map((profile) => profile.imsi) } },
  { _id: 0, imsi: 1, msisdn: 1, subscriber_status: 1, schema_version: 1 }
).sort({ imsi: 1 }).toArray());
JS

echo "Provisionando perfis UE de laboratório sem expor K/OPc..."
kctl -n "${CORE_NAMESPACE}" exec "${MONGODB_POD}" -c mongodb -- \
  mongosh open5gs --quiet --eval "${mongo_script}"

count="$({
  kctl -n "${CORE_NAMESPACE}" exec "${MONGODB_POD}" -c mongodb -- \
    mongosh open5gs --quiet --eval \
    "db.subscribers.countDocuments({imsi:{\$in:['001010000000001','001010000000002','001010000000003']}})"
} | tr -d '\r' | tail -n 1)"

if [[ "${count}" != "3" ]]; then
  echo "Falha: Open5GS retornou ${count} perfis, esperados 3." >&2
  exit 1
fi

echo "UE_LAB_PROFILES_READY count=${count}"

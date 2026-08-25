// MongoDB initialization script for sample Open5GS subscriber data.
// WebUI admin provisioning is handled by the Kubernetes init container.
// This script runs automatically when MongoDB starts for the first time

const subscriberK = process.env.ORAN_SUBSCRIBER_K;
const subscriberOpc = process.env.ORAN_SUBSCRIBER_OPC;
if (!subscriberK || !subscriberOpc) {
    throw new Error('ORAN_SUBSCRIBER_K and ORAN_SUBSCRIBER_OPC are required');
}

db = db.getSiblingDB('open5gs');

// Initialize sample 5G subscriber
// IMSI: 001010000000001 (MCC: 001, MNC: 01, matching .env PLMN config)
try {
    const sub5gResult = db.subscribers.updateOne(
        { imsi: '001010000000001' },
        {
            $setOnInsert: {
                imsi: '001010000000001',
                msisdn: '+82100000001',
                imeisv: '4819690300000000',
                imei: '481969030000000',
                mdn: '',
                urn: 'urn:3gpp:imsi:001010000000001',
                // Subscriber status: 0 = ServiceGranted
                subscriber_status: 0,
                // Network access mode: 0 = PacketAndCircuit
                network_access_mode: 0,
                // Access restriction data
                access_restriction_data: 32,
                operator_determined_barring: 0,
                security: {
                    k: subscriberK,
                    op: null,
                    opc: subscriberOpc,
                    amf: '8000',
                    sqn: NumberLong('0')
                },
                ambr: {
                    downlink: { value: 1, unit: 3 },
                    uplink: { value: 1, unit: 3 }
                },
                slice: [
                    {
                        sst: 1,
                        default_indicator: true,
                        session: [{
                            name: 'internet',
                            type: 3,
                            pcc_rule: [],
                            ambr: {
                                downlink: { value: 1, unit: 3 },
                                uplink: { value: 1, unit: 3 }
                            },
                            qos: {
                                index: 9,
                                arp: {
                                    priority_level: 8,
                                    pre_emption_capability: 1,
                                    pre_emption_vulnerability: 1
                                }
                            }
                        }]
                    }
                ],
                // Schema version for compatibility
                schema_version: 1,
                created_at: new Date(),
                updated_at: new Date()
            }
        },
        { upsert: true }
    );

    if (sub5gResult.upsertedCount === 1) {
        print('Sample 5G subscriber initialized: IMSI 001010000000001');
    } else {
        print('Sample 5G subscriber already exists: IMSI 001010000000001');
    }
} catch (e) {
    print('Sample subscriber info: ' + e.message);
}

// Initialize sample 4G subscriber
// IMSI: 001010000000002
try {
    const sub4gResult = db.subscribers.updateOne(
        { imsi: '001010000000002' },
        {
            $setOnInsert: {
                imsi: '001010000000002',
                msisdn: '+82100000002',
                imeisv: '4819690300000001',
                imei: '481969030000001',
                pdn: [
                    {
                        apn: 'internet',
                        type: 2,
                        qci: 9,
                        arp: {
                            priority_level: 8,
                            pre_emption_capability: 0,
                            pre_emption_vulnerability: 0
                        },
                        mbr: {
                            downlink: 1024,
                            uplink: 1024
                        }
                    }
                ],
                ambr: {
                    downlink: 1024000,
                    uplink: 1024000
                },
                subscriber_status: 0,
                network_access_mode: 0,
                access_restriction_data: 32,
                subscribed_rau_tau_timer: 12,
                schema_version: 1,
                created_at: new Date(),
                updated_at: new Date()
            }
        },
        { upsert: true }
    );

    if (sub4gResult.upsertedCount === 1) {
        print('Sample 4G subscriber initialized: IMSI 001010000000002');
    } else {
        print('Sample 4G subscriber already exists: IMSI 001010000000002');
    }
} catch (e) {
    print('Sample 4G subscriber info: ' + e.message);
}

// Initialize security context for 4G subscriber
try {
    const auth4gResult = db.auths.updateOne(
        { imsi: '001010000000002' },
        {
            $setOnInsert: {
                imsi: '001010000000002',
                k: subscriberK,
                opc: subscriberOpc,
                amf: 32770,
                sqn: 0,
                ck: null,
                ik: null,
                created_at: new Date(),
                updated_at: new Date()
            }
        },
        { upsert: true }
    );

    if (auth4gResult.upsertedCount === 1) {
        print('Security context initialized for 4G subscriber');
    } else {
        print('Security context already exists for 4G subscriber');
    }
} catch (e) {
    print('Security context info: ' + e.message);
}

print('=================================================');
print('MongoDB initialization complete');
print('=================================================');
print('');
print('Sample 5G Subscriber:');
print('  IMSI: 001010000000001');
print('  APN: internet');
print('  K/OPc: loaded from environment');
print('');
print('Sample 4G Subscriber:');
print('  IMSI: 001010000000002');
print('  APN: internet');
print('  K/OPc: loaded from environment');
print('');

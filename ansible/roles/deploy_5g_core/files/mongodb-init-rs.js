// Idempotent replica set initialization for Open5GS lab (single-member rs0).
// Run via deploy_5g_core after MongoDB pod is Ready.

const desiredHost = 'mongodb-0.mongodb:27017';
const localDb = db.getSiblingDB('local');
const existingConfig = localDb.system.replset.findOne({ _id: 'rs0' });

if (existingConfig) {
  if (existingConfig.members[0].host !== desiredHost) {
    existingConfig.version++;
    existingConfig.members[0].host = desiredHost;
    rs.reconfig(existingConfig, { force: true });
    print('reconfigured');
  } else {
    print('already_initialized');
  }
  quit(0);
}

try {
  rs.initiate({
    _id: 'rs0',
    members: [{ _id: 0, host: desiredHost, priority: 1 }]
  });
  print('initialized');
} catch (e) {
  print('init message: ' + e.message);
}

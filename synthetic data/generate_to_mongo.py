#!/usr/bin/env python3
"""
generate_to_mongo.py - generate synthetic cloud-resource data in a NEW MongoDB database.

You choose the database name, date range, and how many spikes and dips to inject.
Every run creates new random data unless you pass --seed (the seed used is always printed and saved).

What gets stored (database --db):
  resources        one document per resource per period, in the Normalized Common Resource Model
                   (user_id, cloud_account_id, provider, account_id, resource_type, resource_id, region, name,
                    configuration, tags, metrics{cpu_average,cpu_p95,memory_average,memory_p95},
                    cost{monthly,currency}, last_synced_at)   <- last_synced_at is a real BSON date; all documents
                    of one snapshot share the same value (23:59 UTC on the snapshot day), so you can group by it
  events           every spike, dip, launch and retirement that was injected (so you can show and query them)

SETUP      pip install pymongo
CONNECT    --uri mongodb://localhost:27017     (or set the MONGO_URI environment variable; Atlas URIs work too)

EXAMPLES
  # new database "walmart_2025" for 2025 with 15 spikes and 4 dips
  python generate_to_mongo.py --db walmart_2025 --start 2025-01-01 --end 2025-12-31 --spikes 15 --dips 4

  # exactly 10,000 documents, bank calendar, repeatable
  python generate_to_mongo.py --db bank_2025 --profile bank --rows 10000 --spikes 20 --seed 7

  # put specific spikes and dips on specific days and resources
  python generate_to_mongo.py --db test1 --spikes 0 --dips 0 \\
        --spike-at 2025-11-28 'store-edge-*' 6  --spike-at 2025-07-09 'web-fe-*' 4 \\
        --dip-at 2025-10-20 'web-fe-*' 0.5

  # only AWS and GCP resources get random spikes, only runaway-cost type, 5x to 15x
  python generate_to_mongo.py --db t2 --spikes 10 --spike-providers aws,gcp --spike-types runaway_cost --spike-size 5 15

  # look around and clean up
  python generate_to_mongo.py --list
  python generate_to_mongo.py --describe walmart_2025
  python generate_to_mongo.py --drop walmart_2025 --yes
  python generate_to_mongo.py --db x --dry-run               # generate and show a summary, store nothing

RULES   The database must not already contain a generated dataset (use --overwrite to replace resources/events).
        Data is stored in the standard "resources" collection so the application can read it after switching
        MONGODB_DATABASE. Documents are inserted in batches, then indexes are created, including a unique one on
        (provider, resource_id, last_synced_at) so the same snapshot can never be stored twice.
"""
import argparse, calendar, collections, fnmatch, json, os, random, re, sys, time
from datetime import date, datetime, timedelta, timezone

D = date.fromisoformat
WD = {'retail': {0: .96, 1: .96, 2: 1.0, 3: 1.02, 4: 1.07, 5: 1.17, 6: 1.12}, 'bank': {0: 1.1, 1: 1.0, 2: .98, 3: 1.0, 4: 1.08, 5: .85, 6: .8}}
SPIKE_TYPES = ('runaway_cost', 'traffic_surge', 'cpu_saturation'); DIP_TYPES = ('outage', 'shutdown')

# ================================================================== calendar of busy and quiet days
def thanksgiving(y): d = date(y, 11, 1); return d + timedelta(days=(3 - d.weekday()) % 7 + 21)
def prev_bd(d):
    while d.weekday() >= 5: d -= timedelta(days=1)
    return d
_PAY = {}
def paydays(y):
    if y not in _PAY: _PAY[y] = {prev_bd(date(y, m, 1)) for m in range(1, 13)} | {prev_bd(date(y, m, 15)) for m in range(1, 13)} | {prev_bd(date(y, m, calendar.monthrange(y, m)[1])) for m in range(1, 13)}
    return _PAY[y]
def day_event(d, profile):
    if profile == 'flat': return 1.0
    y = d.year; tg = thanksgiving(y); bf = tg + timedelta(days=1); md, dd = d.month, d.day; one = timedelta(days=1)
    if profile == 'bank':
        m = 1.0
        if date(y, 2, 10) <= d <= date(y, 4, 15): m = 1.15
        if date(y, 4, 14) <= d <= date(y, 4, 15): m = 1.6
        if md == 1 and dd <= 2: m = 1.2
        if tg - 14 * one <= d < tg: m = 1.2
        m = {tg: 1.5, bf: 3.2, bf + one: 2.5, bf + 2 * one: 2.0, bf + 3 * one: 3.0}.get(d, m)
        if date(y, 12, 15) <= d <= date(y, 12, 23): m = 1.9
        if md == 12 and dd == 25: m = 0.7
        if md == 12 and dd == 26: m = 1.8
        if md == 12 and 27 <= dd <= 31: m = 1.4
        return m * 1.3 if d in paydays(y) else m
    m = 1.0
    if md == 1 and dd == 1: m = 1.1
    if md == 1 and 2 <= dd <= 10: m = 1.3
    if md == 1 and dd >= 11: m = 0.9
    if md == 2 and 10 <= dd <= 14: m = 1.15
    mday = date(y, 5, 1) + timedelta(days=(6 - date(y, 5, 1).weekday()) % 7 + 7)
    if mday - 6 * one <= d <= mday: m = 1.2
    if md == 7 and 8 <= dd <= 13: m = 2.6 if dd in (8, 9) else 2.0
    if md == 8 and dd <= 24: m = 1.3
    if md == 10 and dd >= 27: m = 1.15
    if tg - 14 * one <= d <= tg - 8 * one: m = 1.4
    if tg - 7 * one <= d <= tg - 2 * one: m = 1.7
    m = {tg - one: 1.9, tg: 1.8, bf: 4.0, bf + one: 3.2, bf + 2 * one: 2.6, bf + 3 * one: 3.6, bf + 4 * one: 2.0}.get(d, m)
    if bf + 5 * one <= d <= date(y, 12, 14): m = 1.5
    if date(y, 12, 15) <= d <= date(y, 12, 23): m = 2.2
    if md == 12: m = {24: 1.2, 25: 0.55, 26: 2.1}.get(dd, 1.7 if dd >= 27 else m)
    return m
def drv_value(drv, d, profile):
    on = day_event(d, profile)
    if drv == 'on': return on
    if drv == 'st':
        if profile == 'retail' and (d == thanksgiving(d.year) or (d.month == 12 and d.day == 25)): return 0.1
        return 1 + 0.6 * (on - 1)
    if drv == 'cc': return 1 + 0.5 * (day_event(d - timedelta(days=2), profile) - 1)
    return 1.0

# ================================================================== metric profiles  f(F, r) -> cpu_avg, cpu_p95, mem_avg, mem_p95
cl = lambda x: round(max(0.0, min(99.5, x)), 1)
def P_web(base=26):
    def f(F, r): ca = base * (0.75 + 0.25 * F['s']) * r.uniform(.94, 1.06); ma = 50 * (0.9 + 0.1 * F['s']) * r.uniform(.95, 1.05); return ca, ca + 12 + 14 * (F['pk'] - 1), ma, ma + 10 + 5 * (F['pk'] - 1)
    return f
def P_worker(base=14):
    def f(F, r): ca = base * (0.9 + 0.1 * F['s']) * r.uniform(.9, 1.1); ma = base * 2.1 * r.uniform(.9, 1.1); return ca, ca + 14 + 3 * (F['pk'] - 1), ma, ma + 9
    return f
def P_db(base=36):
    def f(F, r): ca = base * (0.7 + 0.3 * F['s']) * r.uniform(.94, 1.06); ma = 64 * (0.95 + 0.05 * F['s']) * r.uniform(.97, 1.03); return ca, ca + 18 + 8 * (F['pk'] - 1), ma, ma + 8
    return f
def P_cache():
    def f(F, r): ma = 56 * r.uniform(.95, 1.05); ca = 14 * (0.8 + 0.2 * F['s']) * r.uniform(.9, 1.1); return ca, ca + 15 + 6 * (F['pk'] - 1), ma, ma + 9
    return f
def P_k8s(base=38):
    def f(F, r): ca = base * (0.8 + 0.2 * F['s']) * r.uniform(.94, 1.06); ma = 60 * r.uniform(.96, 1.04); return ca, ca + 16 + 10 * (F['pk'] - 1), ma, ma + 10
    return f
def P_batch():
    def f(F, r): ca = 18 * r.uniform(.85, 1.15); ma = 30 * r.uniform(.9, 1.1); return ca, 62 + r.uniform(-6, 6), ma, ma + 24
    return f
def P_low(cpu, mem):
    def f(F, r): ca = cpu * r.uniform(.9, 1.1); ma = mem * r.uniform(.92, 1.08); return ca, ca * 2.5 + 3, ma, ma + 6
    return f
P_none = lambda F, r: (0.0, 0.0, 0.0, 0.0)

# ================================================================== catalog: kinds and resources (edit these to model another business)
def K(rtype, cfg, price, cost='fixed', drv='on', prof=P_none, path=None): return dict(rtype=rtype, cfg=cfg, price=price, cost=cost, drv=drv, prof=prof, path=path)
KINDS = {
 'onprem': {
  'vm_cluster': K('compute_cluster', {'platform': 'vmware', 'hosts': 48}, 85000, prof=P_k8s(36)), 'k8s': K('kubernetes_cluster', {'platform': 'openshift', 'nodes': 260}, 110000, prof=P_k8s(40)),
  'erp_db': K('database', {'engine': 'oracle', 'cores': 128, 'role': 'primary'}, 400000, drv='st', prof=P_db(38)), 'inventory_db': K('database', {'engine': 'postgres', 'shards': 16}, 180000, drv='st', prof=P_db(42)),
  'kafka': K('event_stream', {'engine': 'kafka', 'brokers': 30}, 150000, prof=P_cache()), 'object_store': K('object_storage', {'engine': 'ceph', 'raw_pb': 18}, 90000, 'storage', 'flat'),
  'data_lake': K('data_lake', {'engine': 'hdfs-spark', 'nodes': 300}, 160000, 'batch', 'flat', P_batch()), 'store_edge': K('edge_cluster', {'platform': 'k8s-edge', 'sites_served': 150}, 55000, drv='st', prof=P_web(24)),
  'fc_edge': K('edge_cluster', {'type': 'fulfillment', 'sites': 20}, 25000, prof=P_web(22)), 'cc_tel': K('telephony_cluster', {'sbc': True, 'channels': 3000}, 30000, drv='cc', prof=P_web(28)),
  'cc_crm': K('database', {'engine': 'crm', 'role': 'primary'}, 40000, drv='cc', prof=P_db(34)), 'cc_rec': K('object_storage', {'type': 'call_recordings', 'pb': 1.2}, 35000, 'storage', 'flat'),
  'cc_vdi': K('compute_cluster', {'type': 'agent_desktops', 'seats': 2500}, 22000, drv='cc', prof=P_web(30)), 'dr': K('compute_cluster', {'role': 'disaster_recovery'}, 70000, drv='flat', prof=P_low(14, 35)),
 },
 'aws': {
  'web': K('kubernetes_cluster', {'node_pool': 'web', 'instance_type': 'm6i.4xlarge', 'max_nodes': 300}, 95000, 'auto', 'on', P_web(26), 'eks'), 'order_db': K('database', {'engine': 'aurora-postgres', 'role': 'primary'}, 70000, prof=P_db(36), path='rds'),
  'cache': K('cache_cluster', {'engine': 'redis', 'nodes': 6}, 28000, prof=P_cache(), path='elasticache'), 'cdn': K('cdn_distribution', {'price_class': 'PriceClass_All'}, 150000, 'traffic', path='cloudfront'),
  'waf': K('web_acl', {'rules': 40}, 15000, 'traffic', path='wafv2'), 'apigw': K('api_gateway', {'type': 'HTTP'}, 40000, 'traffic', path='apigateway'), 'lambda': K('serverless_function', {'runtime': 'python3.12'}, 12000, 'traffic', path='lambda'),
  's3': K('object_storage', {'storage_class': 'STANDARD'}, 45000, 'storage', 'flat', path='s3'), 'msk': K('event_stream', {'brokers': 6}, 90000, prof=P_cache(), path='kafka'), 'logs': K('log_group', {'retention_days': 90}, 35000, 'logs', 'flat', path='logs'),
 },
 'azure': {
  'aks': K('kubernetes_cluster', {'node_count': 120, 'vm_size': 'Standard_D16s_v5'}, 90000, 'auto', 'on', P_k8s(36), 'Microsoft.ContainerService/managedClusters'), 'sqlmi': K('database', {'tier': 'BusinessCritical', 'vcores': 80}, 70000, drv='st', prof=P_db(34), path='Microsoft.Sql/managedInstances'),
  'cosmos': K('nosql_table', {'api': 'sql', 'regions': 3}, 80000, 'traffic', 'st', path='Microsoft.DocumentDB/databaseAccounts'), 'openai': K('ai_platform', {'service': 'azure_openai', 'ptu': 100}, 120000, 'traffic', 'on', P_worker(40), 'Microsoft.CognitiveServices/accounts'),
  'blob': K('object_storage', {'sku': 'Standard_GRS'}, 45000, 'storage', 'flat', path='Microsoft.Storage/storageAccounts'), 'databricks': K('data_platform', {'tier': 'premium'}, 110000, 'batch', 'flat', P_batch(), 'Microsoft.Databricks/workspaces'),
  'frontdoor': K('cdn_distribution', {'sku': 'Premium'}, 35000, 'traffic', path='Microsoft.Cdn/profiles'), 'apim': K('api_gateway', {'sku': 'Premium'}, 30000, 'traffic', path='Microsoft.ApiManagement/service'),
  'law': K('monitoring_workspace', {'retention_days': 90}, 40000, 'logs', 'flat', path='Microsoft.OperationalInsights/workspaces'), 'identity': K('identity_service', {'tenant': 'workforce'}, 25000, drv='flat', path='Microsoft.AAD/domainServices'),
  'kv': K('key_vault', {'sku': 'premium'}, 2000, drv='flat', path='Microsoft.KeyVault/vaults'),
 },
 'gcp': {
  'gke': K('kubernetes_cluster', {'node_pool': 'web', 'machine_type': 'n2-standard-16'}, 95000, 'auto', 'on', P_web(26), 'clusters'), 'cloudsql': K('database', {'engine': 'POSTGRES_15', 'ha': True}, 55000, prof=P_db(34), path='instances'),
  'bq': K('data_warehouse', {'pricing': 'editions-enterprise'}, 120000, 'batch', 'flat', path='datasets'), 'gcs': K('object_storage', {'storage_class': 'STANDARD'}, 40000, 'storage', 'flat', path='buckets'),
  'pubsub': K('message_topic', {'retention_hours': 168}, 25000, 'traffic', path='topics'), 'cdn': K('cdn_distribution', {'cache_mode': 'CACHE_ALL_STATIC'}, 150000, 'traffic', path='backendBuckets'),
  'vertex': K('ai_platform', {'machine_type': 'a2-highgpu-1g'}, 140000, 'traffic', 'on', P_worker(38), 'endpoints'), 'logging': K('log_group', {'retention_days': 30}, 35000, 'logs', 'flat', path='buckets'),
  'armor': K('security_policy', {'rules': 40}, 15000, 'traffic', path='securityPolicies'), 'dataflow': K('etl_job', {'max_workers': 200}, 70000, 'batch', 'flat', P_batch(), 'jobs'),
 }}
CATALOG = [  # (provider, kind, name, how many, domain, region)
 ('onprem', 'vm_cluster', 'dc-vm-cluster', 6, 'platform', 'us-dc-1'), ('onprem', 'k8s', 'dc-k8s', 4, 'platform', 'us-dc-2'), ('onprem', 'erp_db', 'erp-db', 1, 'finance', 'us-dc-1'), ('onprem', 'inventory_db', 'inventory-db', 2, 'stores', 'us-dc-1'),
 ('onprem', 'kafka', 'kafka-core', 2, 'platform', 'us-dc-1'), ('onprem', 'object_store', 'object-store', 2, 'platform', 'us-dc-3'), ('onprem', 'data_lake', 'data-lake', 1, 'data-ai', 'us-dc-3'),
 ('onprem', 'store_edge', 'store-edge', 10, 'stores', 'store-edge-region'), ('onprem', 'fc_edge', 'fulfillment-edge', 4, 'supply-chain', 'fulfillment-network'), ('onprem', 'cc_tel', 'cc-telephony', 2, 'customer-service', 'us-dc-1'),
 ('onprem', 'cc_crm', 'cc-crm-db', 1, 'customer-service', 'us-dc-1'), ('onprem', 'cc_rec', 'cc-recordings', 1, 'customer-service', 'us-dc-1'), ('onprem', 'cc_vdi', 'cc-agent-vdi', 1, 'customer-service', 'us-dc-1'), ('onprem', 'dr', 'dr-cluster', 2, 'platform', 'us-dc-2'),
 ('aws', 'web', 'web-fe', 4, 'ecommerce', None), ('aws', 'order_db', 'order-db', 1, 'ecommerce', None), ('aws', 'cache', 'cache', 2, 'ecommerce', None), ('aws', 'cdn', 'cdn-site', 1, 'ecommerce', None), ('aws', 'waf', 'waf-site', 1, 'security', None),
 ('aws', 'apigw', 'api-gw', 1, 'ecommerce', None), ('aws', 'lambda', 'fn-events', 2, 'ecommerce', None), ('aws', 's3', 's3-images', 2, 'ecommerce', None), ('aws', 'msk', 'msk-orders', 1, 'platform', None), ('aws', 'logs', 'cw-logs', 1, 'platform', None),
 ('azure', 'aks', 'aks-api', 3, 'supply-chain', None), ('azure', 'sqlmi', 'sql-mi-inventory', 2, 'stores', None), ('azure', 'cosmos', 'cosmos-inventory', 1, 'stores', None), ('azure', 'openai', 'aoai-assistant', 1, 'data-ai', None),
 ('azure', 'blob', 'blob-supply', 2, 'supply-chain', None), ('azure', 'databricks', 'databricks-sc', 1, 'data-ai', None), ('azure', 'frontdoor', 'fd-apps', 1, 'stores', None), ('azure', 'apim', 'apim-partners', 1, 'supply-chain', None),
 ('azure', 'law', 'law-central', 1, 'platform', None), ('azure', 'identity', 'entra-id', 1, 'security', None), ('azure', 'kv', 'kv-core', 1, 'security', None),
 ('gcp', 'gke', 'web-pool', 4, 'ecommerce', None), ('gcp', 'cloudsql', 'cloudsql-order', 2, 'ecommerce', None), ('gcp', 'bq', 'bq-analytics', 2, 'data-ai', None), ('gcp', 'gcs', 'gcs-lake', 2, 'data-ai', None),
 ('gcp', 'pubsub', 'pubsub-orders', 1, 'ecommerce', None), ('gcp', 'cdn', 'cdn-gcp', 1, 'ecommerce', None), ('gcp', 'vertex', 'vertex-recs', 1, 'data-ai', None), ('gcp', 'logging', 'logging-central', 1, 'platform', None),
 ('gcp', 'armor', 'armor-policy', 1, 'security', None), ('gcp', 'dataflow', 'dataflow-etl', 1, 'data-ai', None),
]
ACC = {'onprem': 'private-cloud', 'aws': '731845209364', 'azure': '2f9a7c14-5b6e-4d38-8a21-c0e7b9f13d65', 'gcp': 'demo-prod-318274'}
DEF_REGION = {'onprem': 'us-dc-1', 'aws': 'us-east-1', 'azure': 'eastus2', 'gcp': 'us-central1'}
PROVIDERS = tuple(KINDS)

def load_catalog(path):
    try: rows = json.load(open(path))
    except (OSError, ValueError) as e: sys.exit(f"Cannot read catalog {path}: {e}")
    out = []
    for e in rows:
        p, k = e.get('provider'), e.get('kind')
        if p not in KINDS or k not in KINDS[p]: sys.exit(f"Catalog entry {e}: unknown provider/kind. Valid kinds: " + '; '.join(f"{pp}: {', '.join(KINDS[pp])}" for pp in KINDS))
        out.append((p, k, e['name'], int(e.get('count', 1)), e.get('domain', 'platform'), e.get('region')))
    return out

def make_periods(start, end, interval):
    out = []
    if interval == 'day':
        d = start
        while d <= end: out.append((d, [d])); d += timedelta(days=1)
    elif interval == 'week':
        d = start + timedelta(days=(6 - start.weekday()))
        while d <= end: out.append((d, [d - timedelta(days=6 - j) for j in range(7)])); d += timedelta(days=7)
    else:
        y, m = start.year, start.month
        while True:
            last = date(y, m, calendar.monthrange(y, m)[1])
            if last > end: break
            if last >= start: out.append((last, [date(y, m, 1) + timedelta(days=j) for j in range(last.day)]))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out

# ================================================================== generation
def generate(a):
    """Returns (documents, events, lifecycle, seed, number_of_periods). Documents hold last_synced_at as an ISO string; the Mongo layer converts it to a date."""
    start, end = D(a.start), D(a.end)
    seed = a.seed if a.seed is not None else str(int(time.time() * 1000) % 10**9)
    PER = make_periods(start, end, a.interval)
    if not PER: sys.exit(f'No {a.interval} snapshots fall between {start} and {end}. Widen the date range or use --interval day.')
    NP = len(PER); ev_rng = random.Random(f"{seed}|events"); rr_for = lambda *p: random.Random("|".join(map(str, (seed,) + p)))
    wd = WD.get(a.profile, {i: 1.0 for i in range(7)}); F = {}
    for drv in ('on', 'st', 'cc', 'flat'):
        F[drv] = []
        for pend, days in PER:
            g = (1 + a.growth) ** ((pend - start).days / 30.0); vals = [drv_value(drv, d, a.profile) for d in days]
            F[drv].append(dict(s=sum(vals) / len(vals) * g, pk=max(1.15, max(v * wd[d.weekday()] for v, d in zip(vals, days)))))
    def batch_f(i):
        days = PER[i][1]; f = 1.0
        if any((d + timedelta(days=1)).day == 1 for d in days): f = 1.25
        if any((d + timedelta(days=1)).day == 1 and d.month in (3, 6, 9, 12) for d in days): f = 1.5
        return f
    cat = load_catalog(a.catalog) if a.catalog else CATALOG
    R = []
    for prov, kind, name, n, dom, reg in cat:
        for i in range(n): R.append(dict(prov=prov, kind=kind, name=name if n == 1 else f"{name}-{i + 1:02d}", domain=dom, region=reg, start=0, end=NP - 1, retired_from=None, burst=False, root=name))
    active = lambda r: max(0, r['end'] - r['start'] + 1); count = lambda: sum(active(r) for r in R)
    core = ('erp_db', 'inventory_db', 'order_db', 'cc_crm', 'identity')
    if a.rows is not None:
        if a.rows < 1: sys.exit('--rows must be positive')
        while count() > a.rows and R:                                  # too many rows: drop random non-core resources
            R.remove(ev_rng.choice([r for r in R if r['kind'] not in core] or R))
        idx = {}
        for r in R:
            try: idx[r['root']] = max(idx.get(r['root'], 0), int(r['name'].rsplit('-', 1)[1]))
            except (ValueError, IndexError): idx[r['root']] = max(idx.get(r['root'], 0), 1)
        fleets = [r for r in R if r['kind'] not in core and KINDS[r['prov']][r['kind']]['cost'] in ('fixed', 'auto')]
        while fleets and count() + NP <= a.rows:                       # too few rows: clone fleet members
            src = ev_rng.choice(fleets); idx[src['root']] = idx.get(src['root'], 1) + 1
            R.append({**src, 'name': f"{src['root']}-{idx[src['root']]:02d}", 'start': 0, 'end': NP - 1})
    life = []; movable = [r for r in R if r['kind'] not in core and not r['burst']]
    if a.rows is None and NP >= 6:
        for r in ev_rng.sample(movable, min(a.launches, len(movable))): r['start'] = ev_rng.randint(1, max(1, int(NP * 0.6))); life.append({'type': 'launch', 'resource': r['name'], 'provider': r['prov'], 'start': PER[r['start']][0].isoformat(), 'note': 'resource starts to exist'})
        base = [x for x in movable if x['start'] == 0]
        for r in ev_rng.sample(base, min(a.retires, len(base))): r['retired_from'] = ev_rng.randint(int(NP * 0.4), NP - 2); life.append({'type': 'retire', 'resource': r['name'], 'provider': r['prov'], 'start': PER[r['retired_from']][0].isoformat(), 'note': 'resource decommissioned (cost and metrics go to 0)'})
    if a.rows is not None:                                             # pad to the exact row count with short-lived autoscaled nodes
        peaks = sorted(range(NP), key=lambda i: -(F['on'][i]['s'] * F['on'][i]['pk'])); j = n = 0
        while count() < a.rows:
            need = a.rows - count(); p0 = peaks[j % min(8, NP)]; j += 1; n += 1; ln = min(3 if need > 3 else need, NP - p0)
            R.append(dict(prov='aws', kind='web', name=f"web-burst-{n:02d}", domain='ecommerce', region=None, start=p0, end=p0 + ln - 1, retired_from=None, burst=True, root='web-burst'))
            if n > 100000: sys.exit('Could not reach --rows')
        assert count() == a.rows
    # ---- spikes and dips
    events = []
    def pool_for(pat, provs):
        pool = [r for r in R if (fnmatch.fnmatchcase(r['name'], pat) if pat else True) and (not provs or r['prov'] in provs)]
        if not pool: sys.exit(f"No resource matches '{pat or '*'}'" + (f" in providers {','.join(provs)}" if provs else ''))
        return pool
    def pick(provs=None):
        pool = pool_for(None, provs); return ev_rng.choices(pool, weights=[KINDS[r['prov']][r['kind']]['price'] * active(r) for r in pool])[0]
    def add_event(typ, r, p0, ln, mult, note):
        p1 = min(NP - 1, p0 + ln - 1); events.append(dict(type=typ, resource=r['name'], provider=r['prov'], start=PER[p0][0].isoformat(), end=PER[p1][0].isoformat(), multiplier=round(mult, 2), note=note, _p0=p0, _p1=p1))
    dur = {'day': (1, 3), 'week': (1, 2), 'month': (1, 1)}[a.interval]
    for _ in range(max(0, a.spikes)):
        r = pick(a.spike_providers); p0 = ev_rng.randint(r['start'], max(r['start'], r['end'])); typ = ev_rng.choices(a.spike_types, weights=[{'runaway_cost': .5, 'traffic_surge': .3, 'cpu_saturation': .2}[t] for t in a.spike_types])[0]
        mult = {'runaway_cost': ev_rng.uniform(*a.spike_size), 'traffic_surge': ev_rng.uniform(2, 4), 'cpu_saturation': ev_rng.uniform(1.2, 2.0)}[typ]; add_event(typ, r, p0, ev_rng.randint(*dur), mult, 'random spike')
    for _ in range(max(0, a.dips)):
        r = pick(a.dip_providers); p0 = ev_rng.randint(r['start'], max(r['start'], r['end'])); typ = ev_rng.choices(a.dip_types, weights=[{'outage': .7, 'shutdown': .3}[t] for t in a.dip_types])[0]
        add_event(typ, r, p0, 1 if typ == 'outage' else ev_rng.randint(*dur), ev_rng.uniform(0.3, 0.7) if typ == 'outage' else 0.12, 'random dip')
    def locate(dtext, flag):
        try: dt = D(dtext)
        except ValueError: sys.exit(f"{flag} needs a date like 2025-11-28, got '{dtext}'")
        p0 = next((i for i, (pend, days) in enumerate(PER) if days[0] <= dt <= pend), None)
        if p0 is None: sys.exit(f'{flag} {dtext} is outside the generated range ({a.start} to {a.end})')
        return p0
    for sa in a.spike_at or []:
        p0 = locate(sa[0], '--spike-at'); pat = sa[1] if len(sa) > 1 else None; mult = float(sa[2]) if len(sa) > 2 else ev_rng.uniform(*a.spike_size)
        for r in (pool_for(pat, None) if pat else [pick(a.spike_providers)]): add_event('runaway_cost', r, p0, 1, mult, 'forced with --spike-at')
    for da in a.dip_at or []:
        p0 = locate(da[0], '--dip-at'); pat = da[1] if len(da) > 1 else None; mult = float(da[2]) if len(da) > 2 else ev_rng.uniform(0.3, 0.7)
        for r in (pool_for(pat, None) if pat else [pick(a.dip_providers)]): add_event('outage', r, p0, 1, mult, 'forced with --dip-at')
    by_res = {}
    for e in events: by_res.setdefault(e['resource'], []).append(e)
    # ---- documents
    docs = []
    for r in R:
        k = KINDS[r['prov']][r['kind']]; prov = r['prov']; reg = r['region'] or DEF_REGION[prov]; hexid = 'i-' + ''.join(rr_for('hex', r['name']).choice('0123456789abcdef') for _ in range(17))
        if prov == 'onprem': rid = f"onprem://{reg}/{r['name']}"
        elif prov == 'aws': rid = f"arn:aws:{k['path'] or 'ec2'}:{reg}:{ACC['aws']}:{r['name']}"
        elif prov == 'azure': rid = f"/subscriptions/{ACC['azure']}/resourceGroups/rg-{r['domain']}/providers/{k['path']}/{r['name']}"
        else: rid = f"projects/{ACC['gcp']}/{k['path']}/{r['name']}"
        for i in range(r['start'], r['end'] + 1):
            rr = rr_for(prov, r['name'], i); pend = PER[i][0]; Fi = dict(F[k['drv']][i]); P = k['price']; c = k['cost']; lm = cm = cpu_m = 1.0; sat = off = False
            for e in by_res.get(r['name'], []):
                if e['_p0'] <= i <= e['_p1']:
                    t = e['type']
                    if t == 'runaway_cost': cm *= e['multiplier']
                    elif t == 'traffic_surge': lm *= e['multiplier']
                    elif t == 'cpu_saturation': sat = True; cm *= e['multiplier']
                    elif t == 'outage': cm *= e['multiplier']; cpu_m *= e['multiplier']
                    elif t == 'shutdown': off = True
            Fi['s'] *= lm; Fi['pk'] = 1 + (Fi['pk'] - 1) * lm
            if c == 'fixed': v = P * rr.uniform(.99, 1.01)
            elif c == 'auto': v = P * (0.55 + 0.45 * max(F[k['drv']][max(0, i - 1)]['s'], Fi['s'])) * rr.uniform(.97, 1.03)
            elif c == 'traffic': v = P * Fi['s'] * rr.uniform(.94, 1.06)
            elif c == 'storage': v = P * (1 + 0.0025 * i * (7 if a.interval == 'week' else 1 if a.interval == 'day' else 30) / 7) * rr.uniform(.995, 1.005)
            elif c == 'logs': v = P * (1.01 ** (i * (1 if a.interval == 'week' else 1 / 7 if a.interval == 'day' else 4))) * (Fi['s'] ** 0.5) * rr.uniform(.95, 1.05)
            else: v = P * (0.8 + 0.2 * batch_f(i)) * rr.uniform(.92, 1.08)
            v *= cm; m = list(k['prof'](Fi, rr)); cfg = dict(k['cfg'])
            if r['burst']: cfg['launched_by'] = 'autoscaler'
            if sat: m = [max(m[0] * 2.2, 84), 99.4, m[2] + 16, 99.0]
            m[0] *= cpu_m
            if off: v *= 0.12; m = [0.0] * 4; cfg['state'] = 'stopped'
            if r['retired_from'] is not None and i >= r['retired_from']: v = 0.0; m = [0.0] * 4; cfg['state'] = 'retired'
            m = [cl(x) for x in m]; m[1] = max(m[1], m[0]); m[3] = max(m[3], m[2])
            docs.append({'user_id': a.user_id, 'cloud_account_id': f"ca_{prov}_demo", 'provider': prov, 'account_id': ACC[prov], 'resource_type': k['rtype'], 'resource_id': hexid if (prov == 'aws' and k['rtype'] == 'compute_instance') else rid,
                         'region': reg, 'name': r['name'], 'configuration': cfg, 'tags': {'env': 'prod', 'team': r['domain'], 'cost_center': 'demo-tech', 'domain': r['domain']},
                         'metrics': {'cpu_average': m[0], 'cpu_p95': m[1], 'memory_average': m[2], 'memory_p95': m[3]}, 'cost': {'monthly': round(max(v, 0.0), 2), 'currency': 'USD'},
                         'last_synced_at': f"{pend.isoformat()}T23:59:00Z"})
    docs.sort(key=lambda d: (d['last_synced_at'][:10], d['provider'], d['resource_id']))
    return docs, [{k: v for k, v in e.items() if not k.startswith('_')} for e in events], life, seed, NP

# ================================================================== MongoDB layer
SCHEMA = {'$jsonSchema': {'bsonType': 'object', 'required': ['user_id', 'provider', 'resource_id', 'name', 'metrics', 'cost', 'last_synced_at'], 'properties': {
    'provider': {'enum': list(PROVIDERS)}, 'last_synced_at': {'bsonType': 'date'},
    'metrics': {'bsonType': 'object', 'properties': {k: {'bsonType': ['double', 'int'], 'minimum': 0, 'maximum': 100} for k in ('cpu_average', 'cpu_p95', 'memory_average', 'memory_p95')}},
    'cost': {'bsonType': 'object', 'required': ['monthly', 'currency'], 'properties': {'monthly': {'bsonType': ['double', 'int'], 'minimum': 0}, 'currency': {'bsonType': 'string'}}}}}}
NAME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,63}$')
def to_dt(s): return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)
def mask(uri): return re.sub(r'//([^:/@]+):[^@]+@', r'//\1:***@', uri)

def connect(uri):
    try: import pymongo
    except ImportError: sys.exit('pymongo is not installed. Run:  pip install pymongo')
    from pymongo.errors import PyMongoError
    try:
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True); client.admin.command('ping')
    except PyMongoError as e: sys.exit(f"Could not connect to MongoDB at {mask(uri)}\n  {str(e)[:300]}\nCheck that MongoDB is running, or pass --uri (or set MONGO_URI).")
    return client

def check_name(name):
    if not NAME_RE.match(name or ''): sys.exit(f"Invalid database name '{name}': start with a letter, then letters, digits or underscore (max 64).")
    if name.lower() in {'admin', 'config', 'local'}: sys.exit(f"'{name}' is a reserved MongoDB database name.")

def store(a, docs, events, life, seed, NP):
    from pymongo.errors import BulkWriteError, PyMongoError
    client = connect(a.uri)
    db = client[a.db]
    existing = set(db.list_collection_names())
    managed = {'resources', 'events'} & existing
    if managed and not a.overwrite:
        sys.exit(f"Database '{a.db}' already contains {', '.join(sorted(managed))}. Choose another --db, or use --overwrite to replace those collections.")
    if a.overwrite:
        for collection in managed:
            db.drop_collection(collection)
    if a.validator:
        try: db.create_collection('resources', validator=SCHEMA, validationLevel='strict'); print('Created resources collection with a JSON-schema validator.')
        except PyMongoError as e: print(f"WARNING: server refused the validator ({str(e)[:80]}...). Creating a plain collection.", file=sys.stderr); db.create_collection('resources')
    else: db.create_collection('resources')
    col = db['resources']; t0 = time.time(); ins = 0; batch = a.batch_size
    for i in range(0, len(docs), batch):
        chunk = [{**d, 'last_synced_at': to_dt(d['last_synced_at'])} for d in docs[i:i + batch]]
        try: ins += len(col.insert_many(chunk, ordered=False).inserted_ids)
        except BulkWriteError as e: print(f"Insert error: {str(e.details.get('writeErrors', [{}])[0].get('errmsg', e))[:200]}", file=sys.stderr); ins += e.details.get('nInserted', 0)
        print(f"  inserted {min(i + batch, len(docs)):>7}/{len(docs)}", end='\r', flush=True)
    print(f"  inserted {ins:>7}/{len(docs)} documents into {a.db}.resources in {time.time() - t0:.1f}s")
    if ins != len(docs): sys.exit('Not all documents were stored; see the error above.')
    col.create_index([('provider', 1), ('resource_id', 1), ('last_synced_at', 1)], unique=True, name='uniq_snapshot')
    col.create_index([('last_synced_at', 1)], name='by_time'); col.create_index([('provider', 1), ('last_synced_at', 1)], name='by_provider_time')
    col.create_index([('name', 1), ('last_synced_at', 1)], name='by_name_time'); col.create_index([('resource_type', 1), ('last_synced_at', 1)], name='by_type_time')
    evdocs = [{**e, 'start': datetime.fromisoformat(e['start']).replace(tzinfo=timezone.utc), **({'end': datetime.fromisoformat(e['end']).replace(tzinfo=timezone.utc)} if 'end' in e else {})} for e in events + life]
    if evdocs:
        db['events'].insert_many(evdocs)
        db['events'].create_index([('type', 1), ('start', 1)], name='by_type_start')
    return col

def cmd_list(a):
    client = connect(a.uri)
    names = [name for name in client.list_database_names() if 'resources' in client[name].list_collection_names()]
    if not names:
        print('No databases containing a resources collection were found.')
        return
    print(f"{'database':<32}{'records':>10}{'resources':>12}")
    for name in names:
        resources = client[name]['resources']
        resource_count = len({(r['provider'], r['resource_id']) for r in resources.find({}, {'provider': 1, 'resource_id': 1})})
        print(f"{name:<32}{resources.count_documents({}):>10}{resource_count:>12}")
def cmd_describe(a):
    client = connect(a.uri)
    db = client[a.describe]
    if 'resources' not in db.list_collection_names(): sys.exit(f"Database '{a.describe}' has no resources collection. Use --list.")
    col = db['resources']
    first = col.find_one(sort=[('last_synced_at', 1)])
    last = col.find_one(sort=[('last_synced_at', -1)])
    resource_count = len({(r['provider'], r['resource_id']) for r in col.find({}, {'provider': 1, 'resource_id': 1})})
    print(f"Database: {a.describe}\nCollection: resources\nDocuments: {col.count_documents({})}\nResources: {resource_count}\nFirst snapshot: {first['last_synced_at']}\nLast snapshot: {last['last_synced_at']}")
    if 'events' in db.list_collection_names():
        print('\nInjected events:')
        for e in db['events'].find({}, {'_id': 0}).sort('start', 1): print(f"  {e['start']:%Y-%m-%d}  {e['type']:<14} {e['resource']:<22}" + (f" x{e['multiplier']}" if 'multiplier' in e else ''))
def cmd_drop(a):
    client = connect(a.uri)
    db = client[a.drop]
    if 'resources' not in db.list_collection_names():
        sys.exit(f"No generated database named '{a.drop}' was found. Use --list.")
    if not a.yes and input(f"Delete the entire database '{a.drop}' and all of its collections? [y/N] ").lower() != 'y': sys.exit('Aborted.')
    client.drop_database(a.drop)
    print(f"Dropped database {a.drop}.")

# ================================================================== command line
def csv_choice(allowed, what):
    def parse(s):
        items = [x.strip() for x in s.split(',') if x.strip()]; bad = [x for x in items if x not in allowed]
        if bad or not items: raise argparse.ArgumentTypeError(f"{what}: choose from {', '.join(allowed)}")
        return items
    return parse
def parse_args():
    a = argparse.ArgumentParser(description='Generate synthetic cloud-resource data in a NEW MongoDB database.', formatter_class=argparse.RawDescriptionHelpFormatter, epilog='Run with --help-full for examples and a full explanation.')
    a.add_argument('--help-full', action='store_true')
    g = a.add_argument_group('the data')
    g.add_argument('--start', default='2025-01-01', help='first date (default 2025-01-01)'); g.add_argument('--end', default='2025-12-31', help='last date (default 2025-12-31)')
    g.add_argument('--interval', choices=['day', 'week', 'month'], default='week'); g.add_argument('--profile', choices=['retail', 'bank', 'flat'], default='retail', help='busy/quiet day calendar')
    g.add_argument('--rows', type=int, help='exact number of documents'); g.add_argument('--seed', help='repeat a previous run'); g.add_argument('--growth', type=float, default=0.02, help='organic growth per month (default 0.02)')
    g.add_argument('--launches', type=int, default=2); g.add_argument('--retires', type=int, default=2); g.add_argument('--user-id', default='user_001'); g.add_argument('--catalog', help='JSON file with your own resource list'); g.add_argument('--print-catalog', action='store_true')
    s = a.add_argument_group('spikes and dips'); s.add_argument('--spikes', type=int, default=10, help='number of random spikes (default 10)'); s.add_argument('--dips', type=int, default=3, help='number of random dips (default 3)')
    s.add_argument('--spike-at', nargs='+', action='append', metavar='DATE [TARGET [MULT]]', help="spike on a date; TARGET = name pattern such as 'web-fe-*'"); s.add_argument('--dip-at', nargs='+', action='append', metavar='DATE [TARGET [MULT]]', help='dip (outage) on a date')
    s.add_argument('--spike-types', type=csv_choice(SPIKE_TYPES, 'spike types'), default=list(SPIKE_TYPES), help='runaway_cost,traffic_surge,cpu_saturation'); s.add_argument('--dip-types', type=csv_choice(DIP_TYPES, 'dip types'), default=list(DIP_TYPES), help='outage,shutdown')
    s.add_argument('--spike-providers', type=csv_choice(PROVIDERS, 'providers'), help='limit random spikes to e.g. aws,gcp'); s.add_argument('--dip-providers', type=csv_choice(PROVIDERS, 'providers'), help='limit random dips')
    s.add_argument('--spike-size', nargs=2, type=float, default=[3.0, 12.0], metavar=('MIN', 'MAX'), help='cost multiplier range for runaway_cost (default 3 12)')
    m = a.add_argument_group('MongoDB'); m.add_argument('--uri', default=os.environ.get('MONGO_URI', 'mongodb://localhost:27017'), help='connection string (default: $MONGO_URI or mongodb://localhost:27017)'); m.add_argument('--db', '--name', dest='db', default=os.environ.get('MONGO_DB'), help='name of the new database (also accepts legacy --name)')
    m.add_argument('--overwrite', action='store_true', help='replace only the resources and events collections'); m.add_argument('--validator', action='store_true', help='create resources with a JSON-schema validator'); m.add_argument('--batch-size', type=int, default=2000)
    m.add_argument('--dry-run', action='store_true', help='generate and summarise, store nothing'); m.add_argument('--json-out', help='also write the documents to this JSON file')
    u = a.add_argument_group('manage databases'); u.add_argument('--list', action='store_true', help='list databases containing a resources collection'); u.add_argument('--describe', metavar='DATABASE', help='show a generated database and its events'); u.add_argument('--drop', metavar='DATABASE', help='delete a generated database'); u.add_argument('--yes', action='store_true')
    return a.parse_args()

def main():
    a = parse_args()
    if a.help_full: print(__doc__); return
    if a.print_catalog: print(json.dumps([dict(provider=p, kind=k, name=n, count=c, domain=d, region=r) for p, k, n, c, d, r in CATALOG], indent=1)); return
    if a.list: cmd_list(a); return
    if a.describe: cmd_describe(a); return
    if a.drop: cmd_drop(a); return
    if not a.db: sys.exit('Choose a database name with --db. Example: --db walmart_2025')
    check_name(a.db)
    try: D(a.start); D(a.end)
    except ValueError: sys.exit('Dates must look like 2025-01-31')
    if D(a.end) < D(a.start): sys.exit('--end must not be before --start')
    if a.spike_size[0] > a.spike_size[1] or a.spike_size[0] <= 0: sys.exit('--spike-size MIN MAX needs 0 < MIN <= MAX')
    docs, events, life, seed, NP = generate(a)
    tot = collections.defaultdict(float)
    for d in docs: tot[d['last_synced_at'][:10]] += d['cost']['monthly']
    pk, lo = max(tot, key=tot.get), min(tot, key=tot.get); nspike = sum(1 for e in events if e['type'] in SPIKE_TYPES); ndip = sum(1 for e in events if e['type'] in DIP_TYPES)
    print(f"Generated {len(docs)} documents: {len({(d['provider'], d['resource_id']) for d in docs})} resources, {NP} {a.interval} snapshots, {a.start} to {a.end}, profile '{a.profile}'")
    print(f"Seed {seed}  (repeat with --seed {seed})")
    print(f"Cost run-rate per snapshot: lowest {tot[lo] / 1e6:.2f}M on {lo}, highest {tot[pk] / 1e6:.2f}M on {pk}")
    print(f"Injected {nspike} spikes, {ndip} dips, {len(life)} launches/retirements:")
    for e in sorted(events + life, key=lambda e: e['start']): print(f"  {e['start']}  {e['type']:<14} {e['resource']:<22} {e['provider']:<7}" + (f" x{e['multiplier']}" if 'multiplier' in e else ''))
    if a.json_out: open(a.json_out, 'w').write('[\n' + ',\n'.join(json.dumps(d, separators=(',', ':')) for d in docs) + '\n]\n'); print(f"Wrote {a.json_out}")
    if a.dry_run: print('\nDry run: nothing stored. First document:\n' + json.dumps(docs[0], indent=1)); return
    print(f"\nStoring in {mask(a.uri)} / {a.db} / resources ...")
    col = store(a, docs, events, life, seed, NP)
    print(f"\nDone. Database '{a.db}' contains resources (data) and events (spikes/dips).\nTry in mongosh:\n  use {a.db}\n  db.resources.find({{}}, {{name:1, 'cost.monthly':1, last_synced_at:1}}).sort({{'cost.monthly': -1}}).limit(5)\n"
          f"  db.resources.aggregate([{{$group: {{_id: '$last_synced_at', total: {{$sum: '$cost.monthly'}}}}}}, {{$sort: {{total: -1}}}}, {{$limit: 5}}])\n  db.events.find().sort({{start: 1}})")

if __name__ == '__main__':
    main()
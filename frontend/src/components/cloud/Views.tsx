import { useMemo, useState, useEffect } from 'react';
import { Link } from '@tanstack/react-router';
import { ArrowDownRight, ArrowRight, ArrowUpRight, CalendarDays, Check, ChevronDown, ChevronLeft, ChevronRight, CircleAlert, Clock3, Cloud, Download, ExternalLink, Eye, Filter, Info, Lightbulb, RefreshCw, Search, Server, ShieldCheck, SlidersHorizontal, Sparkles, TrendingDown, Wallet } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendChart, DistributionChart, Sparkline, UtilizationChart } from './Charts';
import { ProviderBadge, SectionHeading, useCloudApp, useDataset } from './AppShell';
import { money, type Cloud as CloudType, type Finding, type Recommendation, type Period, type Resource } from '@/mockData/cloud';
import { cn } from '@/lib/utils';
import { ConnectionsPanel } from './Connections';
import { ApprovalDrawer, StatusPill } from './Approvals';
import { initialAudit, type ApprovalStatus, type AuditEvent } from '@/mockData/approvals';
import { apiUpdateFindingStatus } from '@/config/api';

function Empty({text='No results match your filters.'}: {text?:string}) {return <div className="empty-state"><Search size={25}/><strong>Nothing to show</strong><span>{text}</span></div>}
function TableControls({query,setQuery,placeholder='Search resources...',filter,setFilter,filters}: {query:string;setQuery:(s:string)=>void;placeholder?:string;filter:string;setFilter:(s:string)=>void;filters:string[]}) {return <div className="table-controls"><div className="search-field"><Search size={15}/><Input value={query} onChange={e=>setQuery(e.target.value)} placeholder={placeholder} aria-label={placeholder}/></div><Select value={filter} onValueChange={setFilter}><SelectTrigger className="filter-select"><Filter size={14}/><SelectValue/></SelectTrigger><SelectContent>{filters.map(f=><SelectItem value={f} key={f}>{f==='All'?'All providers':f}</SelectItem>)}</SelectContent></Select></div>}
function Pager({page,setPage,total,pageSize=5}: {page:number;setPage:(n:number)=>void;total:number;pageSize?:number}) { const pages=Math.max(1,Math.ceil(total/pageSize));return <div className="pager"><span>Showing {total===0?0:(page-1)*pageSize+1}–{Math.min(page*pageSize,total)} of {total}</span><div className="flex gap-1"><Button variant="outline" size="icon" aria-label="Previous page" disabled={page<=1} onClick={()=>setPage(page-1)}><ChevronLeft size={15}/></Button><Button variant="outline" size="icon" aria-label="Next page" disabled={page>=pages} onClick={()=>setPage(page+1)}><ChevronRight size={15}/></Button></div></div> }
function TrendChange({change}: {change:number}) {return <span className={cn('change-pill',change<0?'change-good':'change-bad')}>{change<0?<ArrowDownRight size={13}/>:<ArrowUpRight size={13}/>} {Math.abs(change)}%</span>}

export function CostViewSkeleton({ dashboard, cloud }: { dashboard?: boolean; cloud: CloudType }) {
  return (
    <div className="view-stack animate-fadeIn">
      <div className="callout border-primary/20 bg-primary/5 py-2 px-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-xs text-foreground">
          <RefreshCw size={14} className="animate-spin text-primary shrink-0" />
          <span><strong>Fetching {cloud} cloud analytics...</strong> Calculating spend metrics, resource utilization, and optimization opportunities.</span>
        </div>
        <span className="loading-pulse-badge hidden sm:inline-flex">Live Telemetry</span>
      </div>

      <div className="toolbar-row">
        <div className="period-tabs flex gap-1 p-1 bg-card border border-border rounded-md">
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-7 w-24" />
        </div>
        <Skeleton className="h-4 w-48 hidden sm:block" />
      </div>

      <div className="kpi-grid">
        <div className="surface kpi-card flex flex-col justify-between">
          <div className="kpi-top flex justify-between items-center">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-8 w-8 rounded-md" />
          </div>
          <div className="my-3"><Skeleton className="h-9 w-36" /></div>
          <div className="kpi-foot flex items-center gap-2"><Skeleton className="h-4 w-16 rounded" /><Skeleton className="h-3 w-24" /></div>
        </div>

        <div className="surface kpi-card flex flex-col justify-between">
          <div className="kpi-top flex justify-between items-center">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-8 w-8 rounded-md" />
          </div>
          <div className="my-3"><Skeleton className="h-9 w-36" /></div>
          <div className="kpi-foot flex items-center gap-2"><Skeleton className="h-3 w-3" /><Skeleton className="h-3 w-32" /></div>
        </div>

        <div className="surface kpi-card flex flex-col justify-between">
          <div className="kpi-top flex justify-between items-center">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-8 rounded-md" />
          </div>
          <div className="my-3"><Skeleton className="h-9 w-20" /></div>
          <div className="kpi-foot flex items-center gap-2"><Skeleton className="h-3 w-3" /><Skeleton className="h-3 w-28" /></div>
        </div>
      </div>

      <div className="chart-grid">
        <section className="surface chart-surface">
          <div className="flex items-center justify-between mb-4">
            <div>
              <Skeleton className="h-5 w-28 mb-1.5" />
              <Skeleton className="h-3 w-48" />
            </div>
            <Skeleton className="h-4 w-16 rounded-full" />
          </div>
          <div className="h-[265px] sm:h-[300px] w-full flex flex-col justify-end gap-3 pb-2 pt-6">
            <div className="w-full flex-1 flex items-end justify-between gap-2 px-4">
              {[40, 55, 45, 60, 75, 65, 80, 70, 85, 90, 88, 95].map((h, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end">
                  <div className="w-full rounded-t bg-primary/10 animate-pulse" style={{ height: `${h}%` }} />
                  <Skeleton className="h-2.5 w-6" />
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="surface breakdown-surface">
          <div className="mb-4">
            <Skeleton className="h-5 w-32 mb-1.5" />
            <Skeleton className="h-3 w-28" />
          </div>
          <div className="breakdown-total my-4">
            <Skeleton className="h-3 w-20 mb-2" />
            <Skeleton className="h-5 w-36 mb-1" />
            <Skeleton className="h-7 w-28" />
          </div>
          <div className="flex flex-col gap-3 my-4">
            {[80, 55, 35, 20].map((w, i) => (
              <div key={i} className="flex flex-col gap-1">
                <div className="flex justify-between">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-3 w-10" />
                </div>
                <div className="w-full h-2 rounded bg-secondary overflow-hidden">
                  <div className="h-full bg-primary/20 animate-pulse" style={{ width: `${w}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {dashboard && (
        <div className="insight-strip flex items-center justify-between p-4 surface rounded-lg">
          <div className="flex items-center gap-3">
            <Skeleton className="h-9 w-9 rounded-md" />
            <div>
              <Skeleton className="h-4 w-36 mb-1.5" />
              <Skeleton className="h-3 w-64" />
            </div>
          </div>
          <Skeleton className="h-8 w-28 rounded-md" />
        </div>
      )}

      <section className="surface table-surface">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <Skeleton className="h-5 w-32 mb-1" />
            <Skeleton className="h-3 w-48" />
          </div>
          <Skeleton className="h-6 w-24 rounded" />
        </div>
        <div className="table-controls p-4 flex justify-between">
          <Skeleton className="h-9 w-60 rounded-md" />
          <Skeleton className="h-9 w-24 rounded-md" />
        </div>
        <div className="p-4 flex flex-col gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-border/50">
              <div className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-md" />
                <div>
                  <Skeleton className="h-4 w-36 mb-1" />
                  <Skeleton className="h-3 w-20" />
                </div>
              </div>
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-5 w-14 rounded-full" />
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-4 w-12" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function UnusedViewSkeleton({ cloud }: { cloud: CloudType }) {
  return (
    <div className="view-stack animate-fadeIn">
      <div className="callout border-primary/20 bg-primary/5 py-2.5 px-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-xs text-foreground">
          <RefreshCw size={14} className="animate-spin text-primary shrink-0" />
          <span><strong>Scanning {cloud} services for inactivity signals...</strong> Analyzing CloudWatch / Azure Monitor / Cloud Logging telemetry.</span>
        </div>
        <span className="loading-pulse-badge hidden sm:inline-flex">Evaluating Rules</span>
      </div>

      <div className="summary-band flex items-center justify-between p-6 surface rounded-lg">
        <div className="flex items-center gap-4">
          <Skeleton className="h-12 w-12 rounded-lg" />
          <div>
            <Skeleton className="h-5 w-64 mb-2" />
            <Skeleton className="h-3 w-96 max-w-full" />
          </div>
        </div>
        <div className="text-right">
          <Skeleton className="h-7 w-32 ml-auto mb-1" />
          <Skeleton className="h-3 w-40" />
        </div>
      </div>

      <section className="surface table-surface">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <Skeleton className="h-5 w-48 mb-1" />
            <Skeleton className="h-3 w-64" />
          </div>
          <Skeleton className="h-6 w-24 rounded" />
        </div>
        <div className="table-controls p-4 flex justify-between">
          <Skeleton className="h-9 w-60 rounded-md" />
          <Skeleton className="h-9 w-32 rounded-md" />
        </div>
        <div className="p-4 flex flex-col gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-border/50">
              <div>
                <Skeleton className="h-4 w-40 mb-1" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-5 w-28 rounded-full" />
              <Skeleton className="h-8 w-8 rounded-md" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function UtilizationViewSkeleton({ cloud }: { cloud: CloudType }) {
  return (
    <div className="view-stack animate-fadeIn">
      <div className="callout border-primary/20 bg-primary/5 py-2.5 px-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-xs text-foreground">
          <RefreshCw size={14} className="animate-spin text-primary shrink-0" />
          <span><strong>Evaluating resource rightsizing opportunities for {cloud}...</strong> Inspecting CPU & memory thresholds across instances.</span>
        </div>
        <span className="loading-pulse-badge hidden sm:inline-flex">Telemetry Analysis</span>
      </div>

      <div className="util-top">
        <div className="surface util-chart p-5">
          <div className="flex justify-between items-center mb-4">
            <div>
              <Skeleton className="h-5 w-48 mb-1" />
              <Skeleton className="h-3 w-60" />
            </div>
            <Skeleton className="h-4 w-32" />
          </div>
          <div className="h-[210px] w-full flex items-center justify-center">
            <div className="flex flex-col items-center gap-3 text-muted-foreground">
              <RefreshCw size={24} className="animate-spin text-primary" />
              <span className="text-xs">Computing 14-day utilization curves...</span>
            </div>
          </div>
        </div>

        <div className="surface util-insight p-5 flex flex-col justify-between">
          <Skeleton className="h-9 w-9 rounded-md" />
          <div className="my-3">
            <Skeleton className="h-3 w-36 mb-2" />
            <Skeleton className="h-8 w-40 mb-2" />
            <Skeleton className="h-3 w-52" />
          </div>
          <Skeleton className="h-3 w-44" />
        </div>
      </div>

      <section className="surface table-surface">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <Skeleton className="h-5 w-52 mb-1" />
            <Skeleton className="h-3 w-64" />
          </div>
          <Skeleton className="h-6 w-24 rounded" />
        </div>
        <div className="table-controls p-4 flex justify-between">
          <Skeleton className="h-9 w-60 rounded-md" />
          <Skeleton className="h-9 w-32 rounded-md" />
        </div>
        <div className="p-4 flex flex-col gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center justify-between py-3 border-b border-border/50">
              <div>
                <Skeleton className="h-4 w-44 mb-1" />
                <Skeleton className="h-3 w-28" />
              </div>
              <Skeleton className="h-5 w-16 rounded-full" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-8 rounded-md" />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function RecommendationsViewSkeleton({ cloud }: { cloud: CloudType }) {
  return (
    <div className="view-stack animate-fadeIn">
      <div className="rec-feature relative overflow-hidden flex items-center justify-between p-8">
        <div className="rec-feature-content z-10">
          <div className="flex items-center gap-2 mb-3">
            <RefreshCw size={14} className="animate-spin text-primary" />
            <Skeleton className="h-4 w-48" />
          </div>
          <Skeleton className="h-12 w-56 mb-3" />
          <Skeleton className="h-4 w-72 mb-5" />
          <div className="flex gap-4">
            <Skeleton className="h-4 w-44" />
            <Skeleton className="h-4 w-36" />
          </div>
        </div>
        <div className="rec-feature-art" aria-hidden="true">
          <div className="orbit orbit-one animate-spin" style={{ animationDuration: '20s' }} />
          <div className="orbit orbit-two animate-spin" style={{ animationDuration: '15s', animationDirection: 'reverse' }} />
          <span className="orbit-center"><TrendingDown size={38} className="opacity-40" /></span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {[20, 28, 24, 24, 24, 24].map((w, i) => (
          <Skeleton key={i} className="h-8 rounded-md" style={{ width: `${w * 3.5}px` }} />
        ))}
        <Skeleton className="h-4 w-40 ml-auto" />
      </div>

      <div className="rec-filter-row flex justify-between items-end">
        <div>
          <Skeleton className="h-5 w-44 mb-1.5" />
          <Skeleton className="h-3 w-80" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-8 w-28 rounded-md" />
          <Skeleton className="h-8 w-28 rounded-md" />
        </div>
      </div>

      <div className="recommendations-grid">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="surface recommendation-card flex flex-col justify-between p-5 min-h-[328px]">
            <div>
              <div className="flex justify-between items-center mb-3">
                <Skeleton className="h-8 w-8 rounded-md" />
                <Skeleton className="h-5 w-20 rounded-full" />
              </div>
              <Skeleton className="h-5 w-full mb-1.5" />
              <Skeleton className="h-5 w-3/4 mb-3" />
              <Skeleton className="h-3 w-40 mb-3" />
              <Skeleton className="h-3 w-full mb-1" />
              <Skeleton className="h-3 w-5/6 mb-3" />
              <div className="p-3 bg-secondary/50 rounded-md border border-border/50 my-2">
                <Skeleton className="h-2.5 w-20 mb-1" />
                <Skeleton className="h-3 w-full" />
              </div>
            </div>
            <div className="pt-3 border-t border-border mt-3">
              <div className="flex justify-between items-center mb-3">
                <div>
                  <Skeleton className="h-2.5 w-24 mb-1" />
                  <Skeleton className="h-6 w-20" />
                </div>
                <div className="text-right">
                  <Skeleton className="h-2.5 w-16 mb-1" />
                  <Skeleton className="h-4 w-10 ml-auto" />
                </div>
              </div>
              <div className="flex gap-2">
                <Skeleton className="h-8 flex-1 rounded-md" />
                <Skeleton className="h-8 w-16 rounded-md" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function CostView({dashboard=false}: {dashboard?:boolean}) {
const {providerMeta,services,unused,resources,recommendations}=useDataset(); const {cloud,notify,isFetching}=useCloudApp(); const [period,setPeriod]=useState<Period>('Monthly'); const [from,setFrom]=useState('2026-01-01'); const [to,setTo]=useState('2026-12-31'); const [sort,setSort]=useState<'cost'|'name'|'change'>('cost'); const [ascending,setAscending]=useState(false); const [page,setPage]=useState(1); const [query,setQuery]=useState(''); const meta=providerMeta?.[cloud] ?? { total: 0, average: 0, serviceCount: 0, change: 0, name: cloud, color: 'var(--primary)' }; const list=services?.[cloud] ?? []; const shown=useMemo(()=>list.filter(s=>s.name.toLowerCase().includes(query.toLowerCase())).sort((a,b)=>{const v=sort==='name'?a.name.localeCompare(b.name):a[sort]-b[sort];return ascending?v:-v}),[list,query,sort,ascending]);
 const setSorting=(key:'cost'|'name'|'change')=>{setAscending(sort===key?!ascending:false);setSort(key)};
 if (isFetching) return <CostViewSkeleton dashboard={dashboard} cloud={cloud}/>;
 return <div className="view-stack"><div className="toolbar-row"><div className="period-tabs" role="group" aria-label="Cost period">{(['Daily','Monthly','Custom'] as Period[]).map(p=><Button key={p} variant="ghost" onClick={()=>setPeriod(p)} className={cn('period-button',period===p&&'period-active')}>{p==='Custom'&&<CalendarDays size={13}/>}{p==='Custom'?'Custom range':p}</Button>)}</div><span className="text-xs text-muted-foreground hidden sm:block">{period==='Daily'?'Daily view · Last 30 days':period==='Monthly'?'January – December 2026':'Selected date range'}</span></div>{period==='Custom'&&<div className="date-range"><label>From <Input type="date" value={from} max={to} onChange={e=>setFrom(e.target.value)}/></label><label>To <Input type="date" value={to} min={from} onChange={e=>setTo(e.target.value)}/></label></div>}
 <div className="kpi-grid"><div className="surface kpi-card"><div className="kpi-top"><span>Total Cost</span><span className="kpi-icon"><Wallet size={17}/></span></div><div className="kpi-value">{money(meta.total)}</div><div className="kpi-foot"><TrendChange change={meta.change}/><span>vs. previous period</span></div></div><div className="surface kpi-card"><div className="kpi-top"><span>Average Monthly Cost</span><span className="kpi-icon"><CalendarDays size={17}/></span></div><div className="kpi-value">{money(meta.average)}</div><div className="kpi-foot"><span className="tiny-spark"><span className="h-1 w-1 rounded-full bg-primary"/> Based on last 12 months</span></div></div><div className="surface kpi-card"><div className="kpi-top"><span>Active Services</span><span className="kpi-icon"><Server size={17}/></span></div><div className="kpi-value">{meta.serviceCount}</div><div className="kpi-foot"><span className="tiny-spark"><span className="h-1 w-1 rounded-full bg-success"/> Across {meta.name}</span></div></div></div>
 <div className="chart-grid"><section className="surface chart-surface"><SectionHeading title="Cost trend" detail={`${period==='Daily'?'Daily':'Monthly'} spending over time`} action={<span className="chart-legend"><span style={{background:meta.color}}/>{cloud}</span>}/><TrendChart cloud={cloud} period={period} from={from} to={to}/></section><section className="surface breakdown-surface"><SectionHeading title="Cost breakdown" detail="Spend by service"/><div className="breakdown-total"><span className="breakdown-label">TOP SERVICE</span><strong>{list[0]?.name}</strong><span>{money(list[0]?.cost ?? 0)} <small>this period</small></span></div><DistributionChart services={list} cloud={cloud}/><div className="breakdown-list">{list.slice(0,3).map((s,i)=><div key={s.name}><span><i className={cn('breakdown-dot',i===0?'dot-primary':i===1?'dot-azure':'dot-gcp')}/>{s.name}</span><strong>{Math.round(s.cost/meta.total*100)}%</strong></div>)}</div></section></div>
 {dashboard&&<div className="insight-strip"><div className="insight-icon"><Sparkles size={18}/></div><div><strong>There’s room to optimize</strong><p>{recommendations.filter(r=>r.provider===cloud).length} recommendations could help reduce your {cloud} spending this month.</p></div><Button variant="ghost" asChild className="ml-auto text-primary shrink-0"><Link to="/recommendations">Explore insights <ArrowRight size={15}/></Link></Button></div>}
 <section className="surface table-surface"><SectionHeading title="Service costs" detail={`A closer look at your ${cloud} services`} action={<span className="count-tag">{list.length} SERVICES</span>}/><div className="table-controls"><div className="search-field"><Search size={15}/><Input value={query} onChange={e=>{setQuery(e.target.value);setPage(1)}} placeholder="Search services..." aria-label="Search services"/></div><Button variant="outline" size="sm" className="export-button" onClick={()=>{const csv=['Service,Cost,Change',...shown.map(s=>`"${s.name}",${s.cost},${s.change}`)].join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download=`${cloud.toLowerCase()}-service-costs.csv`;a.click();URL.revokeObjectURL(a.href);notify('Service costs exported.')}}><Download size={14}/> Export</Button></div><div className="table-scroll"><table><thead><tr><th><Button variant="ghost" onClick={()=>setSorting('name')}>SERVICE <ChevronDown size={12}/></Button></th><th><Button variant="ghost" onClick={()=>setSorting('cost')}>COST <ChevronDown size={12}/></Button></th><th><Button variant="ghost" onClick={()=>setSorting('change')}>CHANGE <ChevronDown size={12}/></Button></th><th>TREND</th><th className="text-right">SHARE</th></tr></thead><tbody>{shown.slice((page-1)*5,page*5).map(s=><tr key={s.name}><td className="font-medium text-foreground"><span className="service-icon"><Cloud size={15}/></span>{s.name}</td><td className="font-semibold text-foreground">{money(s.cost)}</td><td><TrendChange change={s.change}/></td><td><Sparkline values={s.trend} positive={s.change>=0}/></td><td className="text-right text-muted-foreground">{(s.cost/meta.total*100).toFixed(1)}%</td></tr>)}</tbody></table>{!shown.length&&<Empty/>}</div><Pager page={page} setPage={setPage} total={shown.length}/></section></div>
}
export function UnusedView() {
 const {unused}=useDataset();
 const {cloud,setCloud,isFetching}=useCloudApp();
 const [query,setQuery]=useState('');
 const [filter,setFilter]=useState<string>(cloud);
 const [page,setPage]=useState(1);
 const [selected,setSelected]=useState<Finding|null>(null);

 useEffect(() => {
   setFilter(cloud);
   setPage(1);
 }, [cloud]);

 if (isFetching) return <UnusedViewSkeleton cloud={cloud}/>;

 const onFilterChange = (v: string) => {
   setFilter(v);
   setPage(1);
   if (v === 'AWS' || v === 'Azure' || v === 'GCP') {
     setCloud(v as CloudType);
   }
 };

 const cloudItems = (unused || []).filter(x => (filter === 'All' ? true : x.provider === filter));
 const rows = cloudItems.filter(x => x.name.toLowerCase().includes(query.toLowerCase()));
 const potential = cloudItems.filter(x => x.status === 'Potentially Unused').length;
 const totalCost = cloudItems.reduce((a,b) => a + b.cost, 0);

 return <div className="view-stack">
   <div className="summary-band">
     <div>
       <span className="summary-icon warning"><CircleAlert size={21}/></span>
       <span>
         <strong>{potential} potentially unused {filter === 'All' ? 'cloud' : filter} services</strong>
         <small>Activity signals suggest these {filter === 'All' ? '' : filter + ' '}services need a closer look—not automatic removal.</small>
       </span>
     </div>
     <div className="summary-stat">
       <strong>{money(totalCost)}</strong>
       <small>{filter === 'All' ? 'total' : filter} monthly cost under review</small>
     </div>
   </div>
   <div className="callout"><Info size={17}/><span>Low cost alone does not mean a {filter === 'All' ? 'cloud' : filter} service is unused. Review activity and ownership before taking action.</span></div>
   <section className="surface table-surface">
     <SectionHeading title={`${filter === 'All' ? 'All' : filter} services to review`} detail={`Activity-based signals across ${filter === 'All' ? 'connected clouds' : filter}`} action={<span className="count-tag">{rows.length} SERVICES</span>}/>
     <TableControls query={query} setQuery={v=>{setQuery(v);setPage(1)}} placeholder={`Search ${filter === 'All' ? '' : filter + ' '}services...`} filter={filter} setFilter={onFilterChange} filters={['All','AWS','Azure','GCP']}/>
     <div className="table-scroll">
       <table>
         <thead>
           <tr><th>SERVICE</th><th>PROVIDER</th><th>CURRENT COST</th><th>LAST ACTIVITY</th><th>STATUS</th><th></th></tr>
         </thead>
         <tbody>
           {rows.slice((page-1)*5,page*5).map(x=><tr key={x.id} className="clickable-row" onClick={()=>setSelected(x)}><td><strong className="text-foreground font-medium block">{x.name}</strong><small>{x.service}</small></td><td><ProviderBadge provider={x.provider}/></td><td className="font-semibold text-foreground">{money(x.cost)}<small>/mo</small></td><td>{x.lastActivity}</td><td><span className={cn('status-pill',x.status==='Potentially Unused'?'status-amber':'status-muted')}>{x.status}</span></td><td><Button variant="ghost" size="icon" aria-label={`View ${x.name}`} onClick={e=>{e.stopPropagation();setSelected(x)}}><ArrowRight size={16}/></Button></td></tr>)}
         </tbody>
       </table>
       {!rows.length&&<Empty text={`No unused services found for ${filter === 'All' ? 'your filters' : filter}.`}/>}
     </div>
     <Pager page={page} setPage={setPage} total={rows.length}/>
   </section>
   <FindingDrawer item={selected} onClose={()=>setSelected(null)}/>
 </div>;
}
function FindingDrawer({item,onClose}: {item:Finding|null;onClose:()=>void}) {return <Sheet open={!!item} onOpenChange={open=>!open&&onClose()}><SheetContent className="detail-drawer overflow-y-auto w-full sm:max-w-[480px]"><SheetHeader><div className="drawer-kicker">SERVICE REVIEW</div><SheetTitle>{item?.name}</SheetTitle><SheetDescription>{item?.service} · {item?.provider}</SheetDescription></SheetHeader>{item&&<div className="drawer-body"><span className="status-pill status-amber">{item.status}</span><div className="drawer-metrics"><div><small>MONTHLY COST</small><strong>{money(item.cost)}</strong></div><div><small>LAST ACTIVITY</small><strong className="text-base">{item.lastActivity}</strong></div></div><div className="drawer-section"><h3>Cost history</h3><div className="history-bars">{item.history.map((v,i)=><div key={i}><span style={{height:`${v/Math.max(...item.history)*85}%`}}/><small>{['May','Jun','Jul','Aug','Sep','Oct'][i]}</small></div>)}</div></div><div className="drawer-section"><h3>Activity & evidence</h3><p>{item.evidence}</p></div><div className="drawer-section"><h3>Recommendation</h3><p>{item.action}</p></div><div className="drawer-note"><Info size={15}/> Activity is an indicator, not proof. Always validate before making changes.</div></div>}</SheetContent></Sheet>}
export function UtilizationView() {
 const {providerMeta,resources}=useDataset();
 const {cloud,setCloud,isFetching}=useCloudApp();
 const [query,setQuery]=useState('');
 const [filter,setFilter]=useState<string>(cloud);
 const [page,setPage]=useState(1);
 const [selected,setSelected]=useState<Resource|null>(null);

 useEffect(() => {
   setFilter(cloud);
   setPage(1);
 }, [cloud]);

 if (isFetching) return <UtilizationViewSkeleton cloud={cloud}/>;

 const onFilterChange = (v: string) => {
   setFilter(v);
   setPage(1);
   if (v === 'AWS' || v === 'Azure' || v === 'GCP') {
     setCloud(v as CloudType);
   }
 };

 const cloudItems = resources.filter(x => (filter === 'All' ? true : x.provider === filter));
 const rows = cloudItems.filter(x => `${x.name} ${x.service}`.toLowerCase().includes(query.toLowerCase()));
 const totalSavings = cloudItems.reduce((a,b) => a + b.savings, 0);
 const activeProvider = (filter === 'All' ? cloud : filter) as CloudType;
 const activeColor = providerMeta[activeProvider]?.color ?? 'var(--primary)';

 return <div className="view-stack">
   <div className="util-top">
     <div className="surface util-chart">
       <SectionHeading title={`${filter === 'All' ? 'Multi-Cloud' : filter} resource utilization`} detail={`Average CPU and memory · last 14 days · ${filter === 'All' ? 'All Providers' : filter}`} action={<div className="legend-inline"><span><i className="dot-primary" style={{background: activeColor}}/>{filter === 'All' ? '' : filter + ' '}CPU</span><span><i className="dot-azure"/>Memory</span></div>}/>
       <UtilizationChart cloud={activeProvider}/>
     </div>
     <div className="surface util-insight">
       <span className="summary-icon green"><TrendingDown size={22}/></span>
       <div>
         <span className="overline">{filter === 'All' ? 'ALL' : filter} POTENTIAL SAVINGS</span>
         <strong>{money(totalSavings)}<small>/month</small></strong>
         <p>Across {cloudItems.length} {filter === 'All' ? '' : filter + ' '}resources with consistently low utilization.</p>
       </div>
       <span className="util-insight-bottom"><ShieldCheck size={15}/> Estimates require validation before changes.</span>
     </div>
   </div>
   <section className="surface table-surface">
     <SectionHeading title={`Underutilized ${filter === 'All' ? 'cloud' : filter} resources`} detail={`Capacity in ${filter === 'All' ? 'your cloud accounts' : filter} that may be larger than needed`} action={<span className="count-tag">{rows.length} RESOURCES</span>}/>
     <TableControls query={query} setQuery={v=>{setQuery(v);setPage(1)}} filter={filter} setFilter={onFilterChange} filters={['All','AWS','Azure','GCP']}/>
     <div className="table-scroll">
       <table>
         <thead>
           <tr><th>RESOURCE</th><th>PROVIDER</th><th>CPU</th><th>MEMORY</th><th>COST</th><th>EST. SAVINGS</th><th></th></tr>
         </thead>
         <tbody>
           {rows.slice((page-1)*5,page*5).map(x=><tr key={x.id} className="clickable-row" onClick={()=>setSelected(x)}><td><strong className="text-foreground font-medium block">{x.name}</strong><small>{x.service}</small></td><td><ProviderBadge provider={x.provider}/></td><td><span className="metric-with-bar">{x.cpu}%<i><b style={{width:`${x.cpu}%`}}/></i></span></td><td><span className="metric-with-bar">{x.memory}%<i><b style={{width:`${x.memory}%`}}/></i></span></td><td className="text-foreground">{money(x.cost)}</td><td className="text-success font-semibold">{money(x.savings)}/mo</td><td><Button variant="ghost" size="icon" aria-label={`View ${x.name}`} onClick={e=>{e.stopPropagation();setSelected(x)}}><ArrowRight size={16}/></Button></td></tr>)}
         </tbody>
       </table>
       {!rows.length&&<Empty text={`No underutilized resources found for ${filter === 'All' ? 'your filters' : filter}.`}/>}
     </div>
     <Pager page={page} setPage={setPage} total={rows.length}/>
   </section>
   <Sheet open={!!selected} onOpenChange={open=>!open&&setSelected(null)}>
     <SheetContent className="detail-drawer overflow-y-auto w-full sm:max-w-[480px]">
       <SheetHeader><div className="drawer-kicker">RESOURCE REVIEW</div><SheetTitle>{selected?.name}</SheetTitle><SheetDescription>{selected?.service} · {selected?.provider}</SheetDescription></SheetHeader>
       {selected&&<div className="drawer-body"><div className="drawer-metrics"><div><small>CPU UTILIZATION</small><strong>{selected.cpu}%</strong></div><div><small>MEMORY UTILIZATION</small><strong>{selected.memory}%</strong></div></div><div className="drawer-section"><h3>Estimated impact</h3><p>Current cost: {money(selected.cost)}/month. Estimated savings: {money(selected.savings)}/month.</p></div><div className="drawer-section"><h3>Suggested action</h3><p>{selected.recommendation}. Validate peak usage and performance requirements first.</p></div></div>}
     </SheetContent>
   </Sheet>
 </div>;
}
export function RecommendationsView() {
 const {providerMeta,recommendations}=useDataset();
 const {cloud,setCloud,notify,isFetching}=useCloudApp();
 const [filter,setFilter]=useState<string>(cloud);
 const [priority,setPriority]=useState('All');
 const [selected,setSelected]=useState<Recommendation|null>(null);
 const [reviewing,setReviewing]=useState<Recommendation|null>(null);
 const [tab,setTab]=useState<'All'|ApprovalStatus>('All');
 const [statuses,setStatuses]=useState<Record<string,ApprovalStatus>>(()=>{try{if(typeof window!=='undefined')return JSON.parse(localStorage.getItem('cloud-advisor-decisions')??'{}')}catch{}return {}});
 const [audits,setAudits]=useState<Record<string,AuditEvent[]>>(()=>{try{if(typeof window!=='undefined')return JSON.parse(localStorage.getItem('cloud-advisor-audits')??'{}')}catch{}return {}});

 useEffect(() => {
   setFilter(cloud);
 }, [cloud]);

 if (isFetching) return <RecommendationsViewSkeleton cloud={cloud}/>;

 const onFilterChange = (v: string) => {
   setFilter(v);
   if (v === 'AWS' || v === 'Azure' || v === 'GCP') {
     setCloud(v as CloudType);
   }
 };

 const statusOf=(id:string)=>statuses[id]??'Pending Review';
 const auditOf=(r:Recommendation)=>audits[r.id]??initialAudit(r);
 const decide=(r:Recommendation,s:ApprovalStatus,text:string)=>{
   const at=new Date().toLocaleString('en-US',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false});
   const nextStatuses={...statuses,[r.id]:s};
   const nextAudits={...audits,[r.id]:[...auditOf(r),{at,actor:'Jordan Davis',text}]};
   setStatuses(nextStatuses);
   setAudits(nextAudits);
   try{
     localStorage.setItem('cloud-advisor-decisions',JSON.stringify(nextStatuses));
     localStorage.setItem('cloud-advisor-audits',JSON.stringify(nextAudits));
   }catch{}
   apiUpdateFindingStatus(r.id,s.toLowerCase(),text).catch(e=>console.warn('Backend status update warning:',e));
   setReviewing(null);
   notify(`${r.title}: ${s}`);
 };

 const cloudItems = recommendations.filter(r => (filter === 'All' ? true : r.provider === filter));
 const rows = cloudItems.filter(r => (priority === 'All' || r.priority === priority) && (tab === 'All' || statusOf(r.id) === tab));
 const pending = cloudItems.filter(r => statusOf(r.id) === 'Pending Review');
 const total = cloudItems.reduce((n,r) => n + r.savings, 0);

 return <div className="view-stack">
   <div className="rec-feature">
     <div className="rec-feature-content">
       <div className="rec-feature-eyebrow"><Sparkles size={14}/> {filter === 'All' ? 'MULTI-CLOUD' : filter} OPTIMIZATION OUTLOOK</div>
       <strong>{money(total)}<span>/mo</span></strong>
       <p>in potential savings across your {filter === 'All' ? 'cloud' : filter} infrastructure</p>
       <div className="rec-feature-meta">
         <span><Check size={14}/> {cloudItems.length} actionable {filter === 'All' ? '' : filter + ' '}recommendations</span>
         <span><ShieldCheck size={14}/> Evidence-backed insights</span>
       </div>
     </div>
     <div className="rec-feature-art" aria-hidden="true">
       <div className="orbit orbit-one"/>
       <div className="orbit orbit-two"/>
       <div className="orbit orbit-three"/>
       <span className="orbit-center"><TrendingDown size={38}/></span>
     </div>
   </div>

   <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Approval status">
     {(['All','Pending Review','Approved','Scheduled','Snoozed','Rejected'] as const).map(t => {
       const n = t === 'All' ? cloudItems.length : cloudItems.filter(r => statusOf(r.id) === t).length;
       return <Button key={t} role="tab" aria-selected={tab===t} size="sm" variant={tab===t?'secondary':'ghost'} onClick={()=>setTab(t)}>
         {t === 'All' ? 'All' : t} <span className="text-muted-foreground">{n}</span>
       </Button>;
     })}
     <span className="ml-auto text-sm text-muted-foreground">Awaiting review: <strong className="text-success">{money(pending.reduce((a,b)=>a+b.savings,0))}/mo</strong></span>
   </div>

   <div className="rec-filter-row">
     <div>
       <h2>{filter === 'All' ? 'All' : filter} recommendations</h2>
       <p>Prioritized opportunities to reduce {filter === 'All' ? 'cloud' : filter} spend without compromising performance.</p>
     </div>
     <div className="flex gap-2">
       <Select value={filter} onValueChange={onFilterChange}>
         <SelectTrigger className="filter-select"><SelectValue/></SelectTrigger>
         <SelectContent>{['All','AWS','Azure','GCP'].map(v=><SelectItem key={v} value={v}>{v==='All'?'All providers':v}</SelectItem>)}</SelectContent>
       </Select>
       <Select value={priority} onValueChange={setPriority}>
         <SelectTrigger className="filter-select"><SelectValue/></SelectTrigger>
         <SelectContent>{['All','High','Medium','Low'].map(v=><SelectItem key={v} value={v}>{v==='All'?'All priorities':`${v} priority`}</SelectItem>)}</SelectContent>
       </Select>
     </div>
   </div>

   <div className="recommendations-grid">
     {rows.map(r => <article className="surface recommendation-card" key={r.id}>
       <div className="rec-card-top">
         <div className="rec-icon"><Lightbulb size={19}/></div>
         <span className="flex gap-1.5 items-center"><StatusPill status={statusOf(r.id)}/><span className={cn('priority-pill',`priority-${r.priority.toLowerCase()}`)}>{r.priority} priority</span></span>
       </div>
       <h3>{r.title}</h3>
       <div className="rec-resource"><ProviderBadge provider={r.provider}/><span>{r.resource}</span></div>
       <p className="rec-problem">{r.problem}</p>
       <div className="rec-evidence"><span>EVIDENCE</span><p>{r.evidence}</p></div>
       <div className="rec-card-bottom">
         <div><small>POTENTIAL SAVINGS</small><strong>{money(r.savings)}<span>/mo</span></strong></div>
         <div className="confidence"><small>CONFIDENCE</small><strong>{r.confidence}%</strong></div>
       </div>
       <div className="rec-actions">
         <Button variant="outline" onClick={()=>setSelected(r)}>View details <ArrowRight size={14}/></Button>
         <Button variant="ghost" onClick={()=>setReviewing(r)}>Review</Button>
       </div>
     </article>)}
     {rows.length===0&&<Empty text={`No recommendations found for ${filter === 'All' ? 'your filters' : filter}.`}/>}
   </div>

   <Sheet open={!!selected} onOpenChange={open=>!open&&setSelected(null)}>
     <SheetContent className="detail-drawer overflow-y-auto w-full sm:max-w-[480px]">
       <SheetHeader><div className="drawer-kicker">OPTIMIZATION OPPORTUNITY</div><SheetTitle>{selected?.title}</SheetTitle><SheetDescription>{selected?.resource} · {selected?.provider}</SheetDescription></SheetHeader>
       {selected&&<div className="drawer-body">
         <div className="flex gap-2"><span className={cn('priority-pill',`priority-${selected.priority.toLowerCase()}`)}>{selected.priority} priority</span><span className="status-pill status-muted">{selected.confidence}% confidence</span></div>
         <div className="drawer-metrics"><div><small>CURRENT COST</small><strong>{money(selected.cost)}</strong></div><div><small>POTENTIAL SAVINGS</small><strong className="text-success">{money(selected.savings)}</strong></div></div>
         <div className="drawer-section"><h3>Why this was detected</h3><p>{selected.problem}</p></div>
         <div className="drawer-section"><h3>Evidence</h3><p>{selected.evidence}</p></div>
         <div className="drawer-section"><h3>Suggested action</h3><p>{selected.action}</p></div>
         <div className="drawer-note"><Info size={15}/> Savings are estimates. Verify workload requirements before making changes.</div>
         <Button className="w-full" onClick={()=>{setReviewing(selected);setSelected(null)}}>Review & decide <ArrowRight size={15}/></Button>
       </div>}
     </SheetContent>
   </Sheet>
   <ApprovalDrawer item={reviewing} status={reviewing?statusOf(reviewing.id):'Pending Review'} audit={reviewing?auditOf(reviewing):[]} onClose={()=>setReviewing(null)} onDecision={(st,t)=>reviewing&&decide(reviewing,st,t)}/>
 </div>;
}
export function AccountView() {
  const { cloud, setCloud, notify, theme, setTheme, user } = useCloudApp();
  const name = user ? user.name : 'Demo User';
  const email = user ? user.email : 'demo@cloudadvisor.io';
  const initials = user ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : 'DU';
  const role = user ? 'Authenticated User' : 'Guest / Demo Mode';

  return <div className="view-stack account-view">
    {!user && (
      <div className="callout flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck size={18} className="text-primary" />
          <span>You are viewing in Demo Mode. Sign in or register to connect your cloud accounts and save your workspace data.</span>
        </div>
        <Button asChild size="sm" variant="outline"><Link to="/login">Sign in</Link></Button>
      </div>
    )}
    <div className="account-identity">
      <div className="avatar-large">{initials}</div>
      <div><h2>{name}</h2><p>{email}</p><span className="role-tag"><ShieldCheck size={13} /> {role}</span></div>
    </div>
    <div className="account-grid">
      <section className="surface account-section">
        <SectionHeading title="Profile details" detail="Your workspace identity" />
        <div className="setting-row"><span>Full name</span><strong>{name}</strong></div>
        <div className="setting-row"><span>Email address</span><strong>{email}</strong></div>
        <div className="setting-row"><span>Role</span><strong>{role}</strong></div>
      </section>
      <section className="surface account-section">
        <SectionHeading title="Preferences" detail="Make Cloud Advisor yours" />
        <div className="setting-row">
          <span>Default cloud</span>
          <Select value={cloud} onValueChange={v => setCloud(v as CloudType)}>
            <SelectTrigger className="account-select"><SelectValue /></SelectTrigger>
            <SelectContent>{(['AWS', 'Azure', 'GCP'] as CloudType[]).map(p => <SelectItem value={p} key={p}>{p}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="setting-row">
          <span>Theme preference</span>
          <Select value={theme} onValueChange={v => { setTheme(v); notify(v === 'Light' ? 'Light theme preference saved for this session.' : 'Dark theme preference saved for this session.') }}>
            <SelectTrigger className="account-select"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="Dark">Dark</SelectItem><SelectItem value="Light">Light</SelectItem></SelectContent>
          </Select>
        </div>
      </section>
    </div>
    <ConnectionsPanel />
  </div>;
}
